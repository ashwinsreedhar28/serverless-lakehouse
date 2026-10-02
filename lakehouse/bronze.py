"""Bronze ingest: data/landing/ → bronze tables. Raw, append-only, with lineage.

    python -m lakehouse.bronze --run-label 2026-10-02_initial [--format delta|parquet] [--force]

What bronze does
- Reads only the landing zone (never the source checkouts) and only files listed in its manifest.
- One table per source record type; one row per natural record (a run, a request, a log line, a CSV row).
- Keeps values as the source has them: CSV columns are strings, JSON scalars keep their JSON type,
  nested JSON objects are stored as a compact JSON string. Nothing is parsed, typed, renamed or deduped.
- Adds four lineage columns to every row:
      ingested_at    when this ingest ran (UTC, same instant for the whole run)
      run_label      the batch tag given on the command line
      source_file    path of the landed file, relative to data/landing/
      source_sha256  sha256 of that landed file (from the manifest, re-verified at read time)
- Append-only, but idempotent: a landed file whose (path, sha256) pair is already present in the target
  table is skipped, so re-running adds nothing; a changed source file (same path, new sha) appends
  alongside the old rows. Two identical files at different paths are both ingested — the source really
  does contain both (results_v0.csv and bench/logs/results_runs1-3.csv are byte-identical); silver dedupes.
  --force disables the skip.
- The ledger (`bronze_ingest_log`) is reconciled at the end of every run: any (table, file, sha) present in a
  data table but missing from the log — a run that died between the data append and the log append — gets a
  log row marked `reconciled`, so a retry repairs the bookkeeping instead of reporting "nothing new".
- Which version of a file is *current* is not bronze's call: the landing manifest is the snapshot, and silver
  selects rows by the manifest's (path, sha256) pairs. Bronze only guarantees every version ever landed is here.

What bronze does not do (silver's job)
- Parse the three worker-log timestamp formats, explode the JSON strings, type the CSV columns,
  map `request_rate: null` to "inf", dedupe results_v0.csv against results_runs1-3.csv.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (BooleanType, DoubleType, IntegerType, LongType, StringType,
                               StructField, StructType, TimestampType)

from .config import BRONZE_TABLES, LANDING_DIR, MANIFEST_PATH, table_path
from .spark import get_spark

# --------------------------------------------------------------------------------------------------
# schemas
# --------------------------------------------------------------------------------------------------

def _s(name: str, t=StringType(), nullable: bool = True) -> StructField:
    return StructField(name, t, nullable)


LINEAGE_FIELDS = [
    _s("ingested_at", TimestampType(), False),
    _s("run_label", StringType(), False),
    _s("source_file", StringType(), False),
    _s("source_sha256", StringType(), False),
]

COLDSTART_HEADER = [
    _s("kind"), _s("mode"), _s("endpoint"), _s("label"), _s("image"), _s("note"),
    _s("max_tokens", LongType()), _s("idle_s", DoubleType()),
]
SCHEMA_COLDSTART_SERIES = StructType(COLDSTART_HEADER + [_s("n_runs", IntegerType()), _s("summary_json")])
SCHEMA_COLDSTART_RUNS = StructType(COLDSTART_HEADER + [
    _s("run_index", IntegerType()), _s("health_before_json"), _s("cold_json"), _s("warm_json"),
])

SWEEP_HEADER = [_s("kind"), _s("system"), _s("server"), _s("base_url"), _s("model"), _s("args_json")]
SCHEMA_SWEEP_RUNS = StructType(SWEEP_HEADER + [
    _s("run_index", IntegerType()), _s("request_rate", DoubleType()), _s("wall_s", DoubleType()),
    _s("summary_json"), _s("trace_json"), _s("server_counters_json"), _s("server_latency_json"),
    _s("n_records", IntegerType()),
])
SCHEMA_SWEEP_RECORDS = StructType([
    _s("system"), _s("run_index", IntegerType()), _s("request_rate", DoubleType()),
    _s("request_id"), _s("arrival_s", DoubleType()), _s("first_token_s", DoubleType()), _s("finish_s", DoubleType()),
    _s("prompt_tokens", LongType()), _s("output_tokens", LongType()), _s("success", BooleanType()), _s("error"),
])
SCHEMA_WORKER_LOG_LINES = StructType([_s("line_no", IntegerType(), False), _s("raw_line", StringType(), False)])
SCHEMA_INGEST_LOG = StructType([
    _s("run_label", StringType(), False), _s("table", StringType(), False), _s("source_file", StringType(), False),
    _s("source_sha256", StringType(), False), _s("rows", LongType(), False), _s("ingested_at", TimestampType(), False),
    _s("reconciled", BooleanType(), False),
])

# Known header rows of the Pulse CSVs. Bronze derives schemas from the files it reads; these lists exist only so a
# silver build over a landing zone that lacks a dataset can still create an empty table with the right columns.
CSV_COLUMNS = {
    "bronze_pulse_coldstart_requests": ["ts_utc", "endpoint_id", "gpu", "model", "kind", "cycle", "req", "wall_ms", "delay_ms", "exec_ms",
                                        "status", "prompt_tokens", "completion_tokens", "finish_reason", "text", "workers_before", "error"],
    "bronze_pulse_throughput_requests": ["ts_utc", "endpoint_id", "gpu", "model", "label", "n", "concurrency", "req", "wall_ms", "delay_ms",
                                         "exec_ms", "status", "prompt_tokens", "completion_tokens", "finish_reason", "score", "error"],
    "bronze_pulse_quality_requests": ["ts_utc", "backend", "model", "label", "host", "gpu", "batch_id", "concurrency", "article_id", "domain",
                                      "wall_ms", "prompt_tokens", "completion_tokens", "finish_reason", "score", "reason", "parse_ok", "text",
                                      "error", "price_unit", "rate_in", "rate_out", "rate_hr", "rate_source", "est_cost_usd", "fixture_sha", "extra"],
    "bronze_pulse_quality_batches": ["batch_id", "ts_utc", "backend", "model", "label", "host", "gpu", "worker_id", "concurrency", "n", "ok",
                                     "parse_ok", "wall_ms", "served_model", "workers_before", "price_unit", "rate_in", "rate_out", "rate_hr",
                                     "rate_source", "est_cost_usd", "fixture_sha", "note"],
}

# landing dataset tag (from manifest) → bronze table(s) fed by it
CSV_TABLE_BY_DATASET = {
    "pulse_coldstart": "bronze_pulse_coldstart_requests",
    "pulse_throughput": "bronze_pulse_throughput_requests",
    "pulse_quality": "bronze_pulse_quality_requests",
    "pulse_quality_batches": "bronze_pulse_quality_batches",
}


def jdump(obj) -> str | None:
    """Nested JSON → compact string. allow_nan keeps the source's NaN literals (Python json wrote them)."""
    return None if obj is None else json.dumps(obj, separators=(",", ":"), allow_nan=True)


# --------------------------------------------------------------------------------------------------
# readers: landed file → {table: DataFrame} with the table's schema (lineage added later)
# --------------------------------------------------------------------------------------------------

def read_coldstart(spark: SparkSession, path: Path) -> dict[str, DataFrame]:
    d = json.loads(path.read_text(encoding="utf-8"))
    header = (d.get("kind"), d.get("mode"), d.get("endpoint"), d.get("label"), d.get("image"), d.get("note"),
              d.get("max_tokens"), d.get("idle_s"))
    runs = d.get("runs", [])
    series = [header + (len(runs), jdump(d.get("summary")))]
    run_rows = [header + (i, jdump(r.get("health_before")), jdump(r.get("cold")), jdump(r.get("warm")))
                for i, r in enumerate(runs)]
    return {
        "bronze_coldstart_series": spark.createDataFrame(series, SCHEMA_COLDSTART_SERIES),
        "bronze_coldstart_runs": spark.createDataFrame(run_rows, SCHEMA_COLDSTART_RUNS),
    }


def read_sweep(spark: SparkSession, path: Path) -> dict[str, DataFrame]:
    d = json.loads(path.read_text(encoding="utf-8"))
    header = (d.get("kind"), d.get("system"), d.get("server"), d.get("base_url"), d.get("model"), jdump(d.get("args")))
    run_rows, rec_rows = [], []
    for i, r in enumerate(d.get("runs", [])):
        recs = r.get("records") or []
        run_rows.append(header + (
            i, r.get("request_rate"), r.get("wall_s"),
            jdump(r.get("summary")), jdump(r.get("trace")), jdump(r.get("server_counters")), jdump(r.get("server_latency")),
            len(recs),
        ))
        for rec in recs:
            rec_rows.append((
                d.get("system"), i, r.get("request_rate"),
                rec.get("request_id"), rec.get("arrival_s"), rec.get("first_token_s"), rec.get("finish_s"),
                rec.get("prompt_tokens"), rec.get("output_tokens"), rec.get("success"),
                None if rec.get("error") is None else str(rec.get("error")),
            ))
    out = {"bronze_sweep_runs": spark.createDataFrame(run_rows, SCHEMA_SWEEP_RUNS)}
    if rec_rows:
        out["bronze_sweep_records"] = spark.createDataFrame(rec_rows, SCHEMA_SWEEP_RECORDS)
    return out


def read_worker_log(spark: SparkSession, path: Path) -> dict[str, DataFrame]:
    lines = path.read_text(encoding="utf-8").splitlines()   # removes line terminators, nothing else
    rows = [(i + 1, line) for i, line in enumerate(lines)]
    return {"bronze_worker_log_lines": spark.createDataFrame(rows, SCHEMA_WORKER_LOG_LINES)}


def read_csv_all_strings(spark: SparkSession, path: Path) -> DataFrame:
    """Spark's CSV reader with an explicit all-string schema taken from the header row.
    multiLine + escape='"' because the `text`/`error` columns hold quoted JSON with embedded quotes."""
    with path.open(newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    schema = StructType([_s(c) for c in header])
    return (spark.read.schema(schema)
            .option("header", "true").option("multiLine", "true")
            .option("quote", '"').option("escape", '"').option("mode", "FAILFAST")
            .csv(str(path)))


def read_csv(spark: SparkSession, path: Path, dataset: str) -> dict[str, DataFrame]:
    return {CSV_TABLE_BY_DATASET[dataset]: read_csv_all_strings(spark, path)}


READERS = {
    "coldstart_series": read_coldstart,
    "sweep": read_sweep,
    "worker_log": read_worker_log,
}


# --------------------------------------------------------------------------------------------------
# table helpers
# --------------------------------------------------------------------------------------------------

def table_exists(name: str) -> bool:
    p = table_path(name)
    return p.is_dir() and any(p.iterdir())


def load_table(spark: SparkSession, fmt: str, name: str) -> DataFrame | None:
    if not table_exists(name):
        return None
    return spark.read.format(fmt).load(str(table_path(name)))


def empty_schema(name: str) -> StructType:
    base = {
        "bronze_coldstart_series": SCHEMA_COLDSTART_SERIES, "bronze_coldstart_runs": SCHEMA_COLDSTART_RUNS,
        "bronze_sweep_runs": SCHEMA_SWEEP_RUNS, "bronze_sweep_records": SCHEMA_SWEEP_RECORDS,
        "bronze_worker_log_lines": SCHEMA_WORKER_LOG_LINES,
    }.get(name) or StructType([_s(c) for c in CSV_COLUMNS[name]])
    return StructType(list(base.fields) + LINEAGE_FIELDS)


def load_or_empty(spark: SparkSession, fmt: str, name: str) -> DataFrame:
    """The bronze table, or an empty frame with its schema when no landed file has fed it yet."""
    df = load_table(spark, fmt, name)
    return df if df is not None else spark.createDataFrame([], empty_schema(name))


def ingested_keys(spark: SparkSession, fmt: str, name: str) -> set[tuple[str, str]]:
    """(source_file, source_sha256) pairs already in the table — the idempotency key."""
    df = load_table(spark, fmt, name)
    if df is None:
        return set()
    return {(r[0], r[1]) for r in df.select("source_file", "source_sha256").distinct().collect()}


def append(df: DataFrame, fmt: str, name: str) -> None:
    w = df.write.format(fmt).mode("append")
    if fmt == "delta":
        w = w.option("mergeSchema", "true")   # a CSV that grows a column must not break the append
    w.save(str(table_path(name)))


def with_lineage(df: DataFrame, ingested_at: datetime, run_label: str, source_file: str, sha: str) -> DataFrame:
    return (df.withColumn("ingested_at", F.lit(ingested_at).cast(TimestampType()))
              .withColumn("run_label", F.lit(run_label))
              .withColumn("source_file", F.lit(source_file))
              .withColumn("source_sha256", F.lit(sha)))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_manifest(landing: Path) -> dict:
    manifest_path = landing / MANIFEST_PATH.name
    if not manifest_path.is_file():
        raise SystemExit(f"no manifest at {manifest_path}; run `make land` first")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def reconcile_ingest_log(spark: SparkSession, fmt: str, run_label: str, ingested_at: datetime) -> int:
    """Append log rows for (table, file, sha) triples that exist in a data table but not in the ledger."""
    log = load_table(spark, fmt, "bronze_ingest_log")
    logged: set[tuple[str, str, str]] = set()
    if log is not None:
        logged = {(r[0], r[1], r[2]) for r in log.select("table", "source_file", "source_sha256").distinct().collect()}
    missing: list[tuple] = []
    for table in BRONZE_TABLES:
        if table == "bronze_ingest_log":
            continue
        df = load_table(spark, fmt, table)
        if df is None:
            continue
        for r in df.groupBy("source_file", "source_sha256").agg(F.count("*").alias("n"), F.min("ingested_at").alias("t")).collect():
            if (table, r["source_file"], r["source_sha256"]) not in logged:
                missing.append((run_label, table, r["source_file"], r["source_sha256"], r["n"], r["t"] or ingested_at, True))
    if missing:
        append(spark.createDataFrame(missing, SCHEMA_INGEST_LOG), fmt, "bronze_ingest_log")
    return len(missing)


# --------------------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-label", required=True, help="batch tag written to every row, e.g. 2026-10-02_initial")
    ap.add_argument("--format", default="delta", choices=["delta", "parquet"])
    ap.add_argument("--force", action="store_true", help="append even if the file's sha256 is already in the table")
    ap.add_argument("--landing-dir", type=Path, default=LANDING_DIR)
    args = ap.parse_args(argv)

    landing: Path = args.landing_dir
    manifest = read_manifest(landing)

    spark = get_spark(args.format, app="bronze-ingest")
    ingested_at = datetime.now(timezone.utc).replace(microsecond=0)
    known = {t: ingested_keys(spark, args.format, t) for t in BRONZE_TABLES if t != "bronze_ingest_log"}

    # Stage every file's frames first, grouped by table, then one append per table (fewer, larger commits).
    staged: dict[str, list[DataFrame]] = {}
    log_rows: list[tuple] = []
    skipped = 0
    for e in manifest["files"]:
        rel, sha, dataset = e["landed_relpath"], e["sha256_landed"], e["dataset"]
        path = landing / rel
        actual = sha256_file(path)
        if actual != sha:
            print(f"bronze: {rel} changed since landing (manifest {sha[:12]}…, file {actual[:12]}…); re-run `make land`",
                  file=sys.stderr)
            return 3
        frames = (read_csv(spark, path, dataset) if dataset in CSV_TABLE_BY_DATASET
                  else READERS[dataset](spark, path))
        for table, df in frames.items():
            if not args.force and (rel, sha) in known[table]:
                skipped += 1
                continue
            df = with_lineage(df, ingested_at, args.run_label, rel, sha)
            staged.setdefault(table, []).append(df)
            log_rows.append((args.run_label, table, rel, sha, df.count(), ingested_at, False))

    if not staged:
        fixed = reconcile_ingest_log(spark, args.format, args.run_label, ingested_at)
        print(f"bronze: nothing new to ingest ({skipped} file→table pairs already present); use --force to re-append"
              + (f"; repaired {fixed} missing ingest-log rows" if fixed else ""))
        spark.stop()
        return 0

    print(f"bronze run_label={args.run_label} format={args.format} ingested_at={ingested_at.isoformat()}")
    for table in BRONZE_TABLES:
        if table not in staged:
            continue
        df = staged[table][0]
        for other in staged[table][1:]:
            df = df.unionByName(other, allowMissingColumns=True)   # schema union across CSV versions
        n = df.count()
        append(df, args.format, table)
        print(f"  {table:<34} +{n:>6} rows  from {len(staged[table])} file(s)")
    append(spark.createDataFrame(log_rows, SCHEMA_INGEST_LOG), args.format, "bronze_ingest_log")
    print(f"  {'bronze_ingest_log':<34} +{len(log_rows):>6} rows")
    fixed = reconcile_ingest_log(spark, args.format, args.run_label, ingested_at)
    if fixed:
        print(f"  repaired {fixed} ingest-log rows missing from an earlier interrupted run")
    if skipped:
        print(f"  skipped {skipped} file→table pairs already ingested (same path and sha256)")
    spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
