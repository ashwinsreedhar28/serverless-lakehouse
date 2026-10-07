"""Bronze on Snowflake: data/landing/ → internal stage → COPY INTO, with the same contract as lakehouse.bronze.

    python -m lakehouse.sf.bronze --run-label 2026-10-08_initial [--force]

Same contract as the Spark bronze
- Reads only the landing zone and only files the manifest lists; re-verifies each file's sha256 before loading.
- One bronze table per source record type, one row per natural record, values as the source has them (CSV columns
  are strings, JSON scalars keep their type, nested JSON is kept as a JSON string), plus the four lineage columns
  ingested_at, run_label, source_file, source_sha256 — and one more, stage_path, the object COPY INTO read.
- Append-only and idempotent on (source_file, source_sha256): a pair already in the target table or in the ledger
  is skipped; a changed file (new sha) appends beside the old rows. --force re-appends (and passes FORCE=TRUE to COPY,
  because Snowflake's own load history would otherwise refuse to load the same stage object twice).
- The ledger `bronze_ingest_log` gets one row per (table, file, sha) append and is reconciled at the end of the run.
- The landing manifest is written to LANDING.MANIFEST_SNAPSHOT (one row per file × expected table, with the expected
  row count) so silver can select the current snapshot and the dbt test can refuse an incomplete bronze.

What is different, and why
- Files are PUT to @LANDING under <sha256[:12]>/<landed_relpath>. The sha is in the path so that Snowflake's load
  history — keyed by stage object, 64 days — and the ledger agree on what "the same file" means.
- Worker logs and the Pulse CSVs are loaded straight into their bronze tables by COPY INTO (one statement per file,
  with the file's own header deciding the column list, so a CSV that grows a column gets the column added first).
- The emberserve JSON documents land whole in `bronze_raw_json` (one VARIANT per file), and the record-grained tables
  (coldstart_series/runs, sweep_runs/records) are carved out with FLATTEN in an INSERT … SELECT right after. COPY INTO's
  transformation SELECT cannot FLATTEN, so this hop is where Snowflake and Spark differ: Spark's reader produced the
  record rows in Python; here the document is the loaded unit and the explode is SQL.
- Every COPY result (rows_parsed, rows_loaded, status) is checked against the plain-Python expected count for that
  file and table at load time, not only in `verify`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from ..config import LANDING_DIR, MANIFEST_PATH
from .client import connect, run
from .counts import CSV_KEY_COLUMNS, CSV_TABLE_BY_DATASET, JSON_DATASETS, csv_header, expected_rows

LINEAGE_DDL = "stage_path STRING, ingested_at TIMESTAMP_NTZ NOT NULL, run_label STRING NOT NULL, source_file STRING NOT NULL, source_sha256 STRING NOT NULL"
LINEAGE_COLS = ["stage_path", "ingested_at", "run_label", "source_file", "source_sha256"]

COLDSTART_HEADER_DDL = "kind STRING, mode STRING, endpoint STRING, label STRING, image STRING, note STRING, max_tokens NUMBER, idle_s DOUBLE"
SWEEP_HEADER_DDL = "kind STRING, system STRING, server STRING, base_url STRING, model STRING, args_json STRING"

TABLE_DDL = {
    "bronze_raw_json": "doc VARIANT NOT NULL",
    "bronze_coldstart_series": f"{COLDSTART_HEADER_DDL}, n_runs NUMBER, summary_json STRING",
    "bronze_coldstart_runs": f"{COLDSTART_HEADER_DDL}, run_index NUMBER, health_before_json STRING, cold_json STRING, warm_json STRING",
    "bronze_sweep_runs": f"{SWEEP_HEADER_DDL}, run_index NUMBER, request_rate DOUBLE, wall_s DOUBLE, summary_json STRING, "
                         "trace_json STRING, server_counters_json STRING, server_latency_json STRING, n_records NUMBER",
    "bronze_sweep_records": "system STRING, run_index NUMBER, request_rate DOUBLE, request_id STRING, arrival_s DOUBLE, first_token_s DOUBLE, "
                            "finish_s DOUBLE, prompt_tokens NUMBER, output_tokens NUMBER, success BOOLEAN, error STRING",
    "bronze_worker_log_lines": "line_no NUMBER NOT NULL, raw_line STRING NOT NULL",
}
# Known Pulse CSV headers (same as lakehouse.bronze.CSV_COLUMNS). The table is created with these; a file whose header has
# more columns gets them added (ALTER TABLE ADD COLUMN) before its COPY — Delta's mergeSchema, spelled out.
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
for _t, _cols in CSV_COLUMNS.items():
    TABLE_DDL[_t] = ", ".join(f"{c} STRING" for c in _cols)

LEDGER_DDL = ("run_label STRING NOT NULL, table_name STRING NOT NULL, source_file STRING NOT NULL, source_sha256 STRING NOT NULL, "
              "n_rows NUMBER NOT NULL, ingested_at TIMESTAMP_NTZ NOT NULL, reconciled BOOLEAN NOT NULL, loader STRING, copy_status STRING")

BRONZE_TABLES = tuple(TABLE_DDL) + ("bronze_ingest_log",)
STAGE = "@LAKEHOUSE.LANDING.LANDING"
FF = "LAKEHOUSE.LANDING."


def lit(s) -> str:
    """SQL string literal. COPY INTO does not take bind variables inside its transformation SELECT."""
    if s is None:
        return "NULL"
    return "'" + str(s).replace("\\", "\\\\").replace("'", "''") + "'"


def ts_lit(dt: datetime) -> str:
    return f"'{dt.strftime('%Y-%m-%d %H:%M:%S')}'::TIMESTAMP_NTZ"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_manifest(landing: Path) -> dict:
    p = landing / MANIFEST_PATH.name
    if not p.is_file():
        raise SystemExit(f"no manifest at {p}; run `make land` first")
    return json.loads(p.read_text(encoding="utf-8"))


def stage_dir(sha: str, rel: str) -> str:
    """@LANDING/<sha12>/<dir of landed_relpath>/ — the sha prefix makes a changed file a new stage object."""
    d = str(Path(rel).parent).replace("\\", "/")
    return f"{STAGE}/{sha[:12]}/{d}/" if d != "." else f"{STAGE}/{sha[:12]}/"


# --------------------------------------------------------------------------------------------------
# tables
# --------------------------------------------------------------------------------------------------

def ensure_tables(cur) -> None:
    for t, ddl in TABLE_DDL.items():
        run(cur, f"CREATE TABLE IF NOT EXISTS BRONZE.{t} ({ddl}, {LINEAGE_DDL})")
    run(cur, f"CREATE TABLE IF NOT EXISTS BRONZE.bronze_ingest_log ({LEDGER_DDL})")
    # the Runpod snapshot table too (lakehouse.sf.runpod fills it), so the dbt runpod models can build before the first poll
    run(cur, f"CREATE TABLE IF NOT EXISTS BRONZE.bronze_runpod_polls (doc VARIANT NOT NULL, {LINEAGE_DDL})")


def table_columns(cur, table: str) -> list[str]:
    return [r[0].lower() for r in run(cur, f"SELECT column_name FROM LAKEHOUSE.information_schema.columns "
                                           f"WHERE table_schema = 'BRONZE' AND table_name = {lit(table.upper())} ORDER BY ordinal_position")]


def ingested_keys(cur, table: str) -> set[tuple[str, str]]:
    """(source_file, source_sha256) pairs already ingested into `table`: data rows, or a ledger entry (a zero-row file's only trace)."""
    keys = {(r[0], r[1]) for r in run(cur, f"SELECT DISTINCT source_file, source_sha256 FROM BRONZE.{table}")}
    keys |= {(r[0], r[1]) for r in run(cur, f"SELECT DISTINCT source_file, source_sha256 FROM BRONZE.bronze_ingest_log WHERE table_name = {lit(table)}")}
    return keys


def write_manifest_snapshot(cur, landing: Path, manifest: dict) -> None:
    """LANDING.MANIFEST_SNAPSHOT: the current (file, sha) pairs and, per file, every bronze table it must be complete in."""
    run(cur, "CREATE OR REPLACE TABLE LANDING.MANIFEST_SNAPSHOT (source_file STRING, source_sha256 STRING, dataset STRING, "
             "expected_table STRING, expected_rows NUMBER, landed_at_utc TIMESTAMP_NTZ, snapshot_written_at TIMESTAMP_NTZ)")
    landed_at = manifest.get("landed_at_utc", "").replace("+00:00", "")
    rows = []
    for e in manifest["files"]:
        for t, n in expected_rows(landing / e["landed_relpath"], e["dataset"]).items():
            rows.append((e["landed_relpath"], e["sha256_landed"], e["dataset"], t, n, landed_at))
    cur.executemany("INSERT INTO LANDING.MANIFEST_SNAPSHOT VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())", rows)


# --------------------------------------------------------------------------------------------------
# loaders: one landed file → rows in one or more bronze tables, via COPY INTO (+ FLATTEN for JSON)
# --------------------------------------------------------------------------------------------------

class CopyResult:
    def __init__(self, row):
        # COPY INTO result columns: file, status, rows_parsed, rows_loaded, error_limit, errors_seen, first_error, ...
        self.file, self.status, self.rows_parsed, self.rows_loaded = row[0], row[1], row[2], row[3]
        self.first_error = row[6] if len(row) > 6 else None


def put_file(cur, path: Path, sha: str, rel: str, force: bool) -> str:
    target = stage_dir(sha, rel)
    rows = run(cur, f"PUT 'file://{path.resolve().as_posix()}' '{target}' AUTO_COMPRESS=TRUE OVERWRITE={'TRUE' if force else 'FALSE'} PARALLEL=4")
    return rows[0][6] if rows else "?"      # UPLOADED | SKIPPED


def copy_into(cur, table: str, select_cols: str, insert_cols: list[str], sha: str, rel: str, fmt: str, force: bool) -> CopyResult:
    gz = Path(rel).name + ".gz"
    sql = (f"COPY INTO BRONZE.{table} ({', '.join(insert_cols)}) "
           f"FROM (SELECT {select_cols} FROM {stage_dir(sha, rel)}) "
           f"FILES = ({lit(gz)}) FILE_FORMAT = (FORMAT_NAME = '{FF}{fmt}') ON_ERROR = ABORT_STATEMENT FORCE = {'TRUE' if force else 'FALSE'}")
    rows = run(cur, sql)
    if not rows:
        raise SystemExit(f"bronze: COPY INTO {table} from {rel} returned no result row")
    return CopyResult(rows[0])


def lineage_select(ingested_at: datetime, run_label: str, rel: str, sha: str) -> str:
    return f"METADATA$FILENAME, {ts_lit(ingested_at)}, {lit(run_label)}, {lit(rel)}, {lit(sha)}"


def load_worker_log(cur, path, rel, sha, ctx) -> dict[str, tuple[int, str, str]]:
    r = copy_into(cur, "bronze_worker_log_lines", f"METADATA$FILE_ROW_NUMBER, $1, {lineage_select(*ctx, rel, sha)}",
                  ["line_no", "raw_line", *LINEAGE_COLS], sha, rel, "FF_LOG_LINES", ctx.force)
    return {"bronze_worker_log_lines": (r.rows_loaded, "copy_into", r.status)}


def load_csv(cur, path, rel, sha, dataset, ctx) -> dict[str, tuple[int, str, str]]:
    table = CSV_TABLE_BY_DATASET[dataset]
    header = csv_header(path)
    missing = [c for c in CSV_KEY_COLUMNS[table] if c not in header]
    if missing:
        raise SystemExit(f"bronze: {path.name} is tagged dataset={dataset!r} (→ {table}) but its header lacks the key columns {missing}.\n"
                         f"  file header: {header}\n  If the Pulse CSV layout changed on purpose, update CSV_COLUMNS/CSV_KEY_COLUMNS; "
                         f"if the tag is wrong, fix land.py.")
    have = table_columns(cur, table)
    for c in header:
        if c.lower() not in have:
            print(f"  note: {path.name} has column {c!r} not yet in {table}; adding it (schema merges on append)")
            run(cur, f"ALTER TABLE BRONZE.{table} ADD COLUMN {c} STRING")
    positional = ", ".join(f"${i + 1}" for i in range(len(header)))
    r = copy_into(cur, table, f"{positional}, {lineage_select(*ctx, rel, sha)}", [*header, *LINEAGE_COLS], sha, rel, "FF_PULSE_CSV", ctx.force)
    return {table: (r.rows_loaded, "copy_into", r.status)}


# JSON string columns: Spark kept nested objects as compact JSON strings and SQL NULL for a missing/null key.
def js(expr: str) -> str:
    return f"IFF({expr} IS NULL OR IS_NULL_VALUE({expr}), NULL, TO_JSON({expr}))"


def st(expr: str) -> str:
    """A scalar the source may have written as a string or as something else (sweep `error` can be an object)."""
    return f"IFF({expr} IS NULL OR IS_NULL_VALUE({expr}), NULL, IFF(IS_VARCHAR({expr}), {expr}::STRING, TO_JSON({expr})))"


COLDSTART_HEADER_SEL = ("doc:kind::STRING, doc:mode::STRING, doc:endpoint::STRING, doc:label::STRING, doc:image::STRING, doc:note::STRING, "
                        "doc:max_tokens::NUMBER, doc:idle_s::DOUBLE")
SWEEP_HEADER_SEL = f"doc:kind::STRING, doc:system::STRING, doc:server::STRING, doc:base_url::STRING, doc:model::STRING, {js('doc:args')}"

FLATTEN_SQL = {
    "bronze_coldstart_series": f"""
        INSERT INTO BRONZE.bronze_coldstart_series
        SELECT {COLDSTART_HEADER_SEL}, ARRAY_SIZE(COALESCE(doc:runs, ARRAY_CONSTRUCT())), {js('doc:summary')},
               stage_path, ingested_at, run_label, source_file, source_sha256
        FROM BRONZE.bronze_raw_json {{where}}""",
    "bronze_coldstart_runs": f"""
        INSERT INTO BRONZE.bronze_coldstart_runs
        SELECT {COLDSTART_HEADER_SEL}, r.index, {js('r.value:health_before')}, {js('r.value:cold')}, {js('r.value:warm')},
               stage_path, ingested_at, run_label, source_file, source_sha256
        FROM BRONZE.bronze_raw_json, LATERAL FLATTEN(input => doc:runs) r {{where}}""",
    "bronze_sweep_runs": f"""
        INSERT INTO BRONZE.bronze_sweep_runs
        SELECT {SWEEP_HEADER_SEL}, r.index, r.value:request_rate::DOUBLE, r.value:wall_s::DOUBLE,
               {js('r.value:summary')}, {js('r.value:trace')}, {js('r.value:server_counters')}, {js('r.value:server_latency')},
               ARRAY_SIZE(COALESCE(r.value:records, ARRAY_CONSTRUCT())),
               stage_path, ingested_at, run_label, source_file, source_sha256
        FROM BRONZE.bronze_raw_json, LATERAL FLATTEN(input => doc:runs) r {{where}}""",
    "bronze_sweep_records": f"""
        INSERT INTO BRONZE.bronze_sweep_records
        SELECT doc:system::STRING, r.index, r.value:request_rate::DOUBLE,
               rec.value:request_id::STRING, rec.value:arrival_s::DOUBLE, rec.value:first_token_s::DOUBLE, rec.value:finish_s::DOUBLE,
               rec.value:prompt_tokens::NUMBER, rec.value:output_tokens::NUMBER, rec.value:success::BOOLEAN, {st('rec.value:error')},
               stage_path, ingested_at, run_label, source_file, source_sha256
        FROM BRONZE.bronze_raw_json, LATERAL FLATTEN(input => doc:runs) r, LATERAL FLATTEN(input => r.value:records) rec {{where}}""",
}
JSON_TABLES_BY_DATASET = {
    "coldstart_series": ["bronze_coldstart_series", "bronze_coldstart_runs"],
    "sweep": ["bronze_sweep_runs", "bronze_sweep_records"],
}


def load_json(cur, path, rel, sha, dataset, ctx, wanted: set[str]) -> dict[str, tuple[int, str, str]]:
    out: dict[str, tuple[int, str, str]] = {}
    ingested_at, run_label = ctx.ingested_at, ctx.run_label
    if "bronze_raw_json" in wanted:
        r = copy_into(cur, "bronze_raw_json", f"$1, {lineage_select(ingested_at, run_label, rel, sha)}", ["doc", *LINEAGE_COLS],
                      sha, rel, "FF_JSON_DOC", ctx.force)
        out["bronze_raw_json"] = (r.rows_loaded, "copy_into", r.status)
    # Carve the record tables out of the *latest* ingest of this (file, sha) document: this run's, normally; an earlier
    # run's when that run died between the raw COPY and the explode (the ledger then lacks the derived table and we get
    # here with bronze_raw_json not in `wanted`). The ingested_at of the derived rows is the raw document's.
    where = (f"WHERE source_file = {lit(rel)} AND source_sha256 = {lit(sha)} AND ingested_at = "
             f"(SELECT MAX(ingested_at) FROM BRONZE.bronze_raw_json WHERE source_file = {lit(rel)} AND source_sha256 = {lit(sha)})")
    for t in JSON_TABLES_BY_DATASET[dataset]:
        if t not in wanted:
            continue
        run(cur, FLATTEN_SQL[t].format(where=where))
        out[t] = (cur.rowcount or 0, "insert_flatten", "FROM bronze_raw_json")
    return out


# --------------------------------------------------------------------------------------------------
# ledger
# --------------------------------------------------------------------------------------------------

def reconcile_ingest_log(cur, run_label: str, ingested_at: datetime) -> int:
    """Ledger rows for (table, file, sha) triples present in a data table but missing from the log."""
    fixed = 0
    for t in TABLE_DDL:
        run(cur, f"""
            INSERT INTO BRONZE.bronze_ingest_log (run_label, table_name, source_file, source_sha256, n_rows, ingested_at, reconciled, loader, copy_status)
            SELECT {lit(run_label)}, {lit(t)}, d.source_file, d.source_sha256, COUNT(*), COALESCE(MIN(d.ingested_at), {ts_lit(ingested_at)}), TRUE, 'reconciled', NULL
            FROM BRONZE.{t} d
            LEFT JOIN BRONZE.bronze_ingest_log l
              ON l.table_name = {lit(t)} AND l.source_file = d.source_file AND l.source_sha256 = d.source_sha256
            WHERE l.source_file IS NULL
            GROUP BY d.source_file, d.source_sha256""")
        fixed += cur.rowcount or 0
    return fixed


# --------------------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------------------

class Ctx:
    def __init__(self, ingested_at: datetime, run_label: str, force: bool):
        self.ingested_at, self.run_label, self.force = ingested_at, run_label, force

    def __iter__(self):       # lineage_select(*ctx, …)
        yield self.ingested_at
        yield self.run_label


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-label", required=True, help="batch tag written to every row, e.g. 2026-10-08_initial")
    ap.add_argument("--force", action="store_true", help="append even if the file's (path, sha256) is already in the table; COPY … FORCE=TRUE")
    ap.add_argument("--landing-dir", type=Path, default=LANDING_DIR)
    args = ap.parse_args(argv)

    landing: Path = args.landing_dir
    manifest = read_manifest(landing)
    ingested_at = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
    ctx = Ctx(ingested_at, args.run_label, args.force)

    conn = connect("BRONZE")
    cur = conn.cursor()
    try:
        ensure_tables(cur)
        write_manifest_snapshot(cur, landing, manifest)
        known = {t: ingested_keys(cur, t) for t in TABLE_DDL}

        print(f"bronze(snowflake) run_label={args.run_label} ingested_at={ingested_at.isoformat()}Z files={len(manifest['files'])}")
        log_rows: list[tuple] = []
        skipped = loaded_files = mismatches = 0
        per_table: dict[str, int] = {}
        for e in manifest["files"]:
            rel, sha, dataset = e["landed_relpath"], e["sha256_landed"], e["dataset"]
            path = landing / rel
            if not path.is_file():
                print(f"bronze: {rel} is in the manifest but missing from {landing}; re-run `make land`", file=sys.stderr)
                return 3
            actual = sha256_file(path)
            if actual != sha:
                print(f"bronze: {rel} changed since landing (manifest {sha[:12]}…, file {actual[:12]}…); re-run `make land`", file=sys.stderr)
                return 3
            expected = expected_rows(path, dataset)
            wanted = {t for t in expected if args.force or (rel, sha) not in known[t]}
            skipped += len(expected) - len(wanted)
            if not wanted:
                continue

            put_status = put_file(cur, path, sha, rel, args.force)
            if dataset == "worker_log":
                got = load_worker_log(cur, path, rel, sha, ctx)
            elif dataset in CSV_TABLE_BY_DATASET:
                got = load_csv(cur, path, rel, sha, dataset, ctx)
            elif dataset in JSON_DATASETS:
                got = load_json(cur, path, rel, sha, dataset, ctx, wanted)
            else:
                raise SystemExit(f"bronze: unknown dataset tag {dataset!r} for {rel}")
            loaded_files += 1
            for t, (n, loader, status) in got.items():
                # Snowflake's load history refused a file the ledger does not know (e.g. the table was recreated but the
                # stage kept its history): say so, then load it with FORCE so the table and the ledger agree again.
                if loader == "copy_into" and status == "LOAD_SKIPPED" and n == 0 and expected[t] > 0:
                    print(f"  {t:<34} {rel}: load history already has this object but the table does not; reloading with FORCE=TRUE")
                    ctx_f = Ctx(ingested_at, args.run_label, True)
                    redo = (load_worker_log(cur, path, rel, sha, ctx_f) if dataset == "worker_log"
                            else load_csv(cur, path, rel, sha, dataset, ctx_f) if dataset in CSV_TABLE_BY_DATASET
                            else load_json(cur, path, rel, sha, dataset, ctx_f, {t}))
                    n, loader, status = redo[t]
                    status = f"{status} (after LOAD_SKIPPED)"
                ok = n == expected[t]
                mismatches += 0 if ok else 1
                per_table[t] = per_table.get(t, 0) + n
                log_rows.append((args.run_label, t, rel, sha, n, ingested_at, False, loader, status))
                flag = "" if ok else f"   <-- expected {expected[t]} (MISMATCH)"
                print(f"  {t:<34} +{n:>6} rows  {rel}  put={put_status} {status}{flag}")

        if log_rows:
            cur.executemany("INSERT INTO BRONZE.bronze_ingest_log VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", log_rows)
            print(f"  {'bronze_ingest_log':<34} +{len(log_rows):>6} rows")
        fixed = reconcile_ingest_log(cur, args.run_label, ingested_at)
        if fixed:
            print(f"  repaired {fixed} ingest-log rows missing from an earlier interrupted run")
        if not log_rows:
            print(f"bronze: nothing new to ingest ({skipped} file→table pairs already present); use --force to re-append")
        else:
            print("bronze: loaded " + ", ".join(f"{t} +{n}" for t, n in per_table.items()))
            if skipped:
                print(f"  skipped {skipped} file→table pairs already ingested (same path and sha256)")
        if mismatches:
            print(f"bronze: {mismatches} file→table pair(s) loaded a different row count than the file holds — see MISMATCH above", file=sys.stderr)
            return 4
        return 0
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
