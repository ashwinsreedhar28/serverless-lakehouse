"""Silver: bronze → typed, parsed, deduplicated tables, one row per *event*, joinable across sources.

    python -m lakehouse.silver [--format delta|parquet]

What silver does
- Reads bronze (never landing) and the committed seeds in seeds/.
- Selects, per source file, the rows of the version the landing manifest names right now — the
  (path, sha256) pairs in data/landing/manifest.json. Bronze is a ledger and may hold several versions of a
  file, including a renamed path or a version with no records; the manifest is the snapshot that says which
  one is current. A manifest file whose version is missing from bronze stops the build (run `make bronze`).
- Types every column, explodes the JSON strings bronze kept, parses the three worker-log timestamp formats
  to UTC, normalises names that differ between sources (`qwen/qwen3-8b` and `Qwen3-8B` are one model),
  and dedupes the byte-identical Pulse CSVs.
- Derives the handful of fields gold needs: `is_flashboot_hit`, `billed_s`, `est_cost_usd`, `ttft_ms`.
- Is rebuilt from scratch on every run (`overwrite`): silver is a deterministic function of bronze + seeds,
  so there is nothing to append. Every row carries `silver_built_at` and bronze's `source_file`.

Silver is where opinions start: thresholds, cost formulas and name mappings live here and are listed in
the README's decisions section.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql import types as T

from .bronze import load_or_empty, load_table, read_manifest
from .config import BRONZE_TABLES, CONSOLE_LOG_TZ, FLASHBOOT_HIT_MS, LANDING_DIR, SEEDS_DIR, SILVER_TABLES, table_path
from .spark import get_spark

# --------------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------------

_SNAPSHOT: DataFrame | None = None


def set_snapshot(spark: SparkSession, manifest: dict) -> None:
    """The current (source_file, source_sha256) pairs, from the landing manifest."""
    global _SNAPSHOT
    pairs = [(e["landed_relpath"], e["sha256_landed"]) for e in manifest["files"]]
    _SNAPSHOT = spark.createDataFrame(pairs, "source_file string, source_sha256 string").cache()


def latest_per_file(df: DataFrame) -> DataFrame:
    """Keep only the rows whose (source_file, source_sha256) the landing manifest names as current.

    Named for what it used to do (max ingested_at per file); that broke on a reverted file (A→B→A re-appends
    nothing, so B stayed newest), on a replacement with no records, and on a rename. Joining to the manifest
    handles all three and never depends on ingest timestamps.
    """
    assert _SNAPSHOT is not None, "set_snapshot() must run before any silver builder"
    return df.join(_SNAPSHOT, ["source_file", "source_sha256"], "inner")


def assert_snapshot_in_bronze(spark: SparkSession, fmt: str, manifest: dict) -> None:
    """Every manifest (file, sha) must exist in at least one bronze data table, or silver would silently drop it."""
    present: set[tuple[str, str]] = set()
    for t in BRONZE_TABLES:
        if t == "bronze_ingest_log":
            continue
        df = load_table(spark, fmt, t)
        if df is not None:
            present |= {(r[0], r[1]) for r in df.select("source_file", "source_sha256").distinct().collect()}
    missing = [e["landed_relpath"] for e in manifest["files"] if (e["landed_relpath"], e["sha256_landed"]) not in present]
    if missing:
        raise SystemExit(f"silver: {len(missing)} landed file(s) are not in bronze at their current sha256 — run `make bronze` first: "
                         + ", ".join(missing[:5]) + (" …" if len(missing) > 5 else ""))


def read_seed(spark: SparkSession, name: str, schema: T.StructType) -> DataFrame:
    return (spark.read.schema(schema).option("header", "true").option("quote", '"').option("escape", '"')
            .option("nullValue", "").option("emptyValue", None)
            .csv(str(SEEDS_DIR / f"{name}.csv")))


def write(df: DataFrame, fmt: str, name: str) -> int:
    df = df.withColumn("silver_built_at", F.lit(BUILT_AT).cast(T.TimestampType()))
    w = df.write.format(fmt).mode("overwrite")
    if fmt == "delta":
        w = w.option("overwriteSchema", "true")   # silver's schema is allowed to evolve between builds
    w.save(str(table_path(name)))
    return df.count()


def canonical_model(col):
    """One name per model across sources. Pulse writes HF ids in two casings; emberserve series use short names."""
    low = F.lower(col)
    return (F.when(low.isin("qwen/qwen3-8b"), "Qwen3-8B")
             .when(low.isin("qwen/qwen3-32b-awq"), "Qwen3-32B-AWQ")
             .when(low.isin("qwen/qwen2.5-7b", "qwen2.5-7b"), "Qwen2.5-7B")
             .when(low.isin("qwen/qwen2.5-0.5b", "qwen2.5-0.5b"), "Qwen2.5-0.5B")
             .otherwise(col))


BUILT_AT = datetime.now(timezone.utc).replace(microsecond=0)

# --------------------------------------------------------------------------------------------------
# seeds → dims
# --------------------------------------------------------------------------------------------------

SEED_SERIES = T.StructType([
    T.StructField("series_label", T.StringType()), T.StructField("engine", T.StringType()),
    T.StructField("engine_build", T.StringType()), T.StructField("model", T.StringType()),
    T.StructField("gpu_model", T.StringType()), T.StructField("flashboot", T.StringType()),
    T.StructField("flashboot_source", T.StringType()), T.StructField("weights_mode", T.StringType()),
    T.StructField("image_gb", T.DoubleType()), T.StructField("notes", T.StringType()),
])
SEED_RUN_NOTES = T.StructType([
    T.StructField("series_label", T.StringType()), T.StructField("run_index", T.IntegerType()),
    T.StructField("host_state", T.StringType()), T.StructField("evidence", T.StringType()),
    T.StructField("note", T.StringType()), T.StructField("source", T.StringType()),
])
SEED_GPU = T.StructType([
    T.StructField("gpu_label", T.StringType()), T.StructField("tier", T.StringType()),
    T.StructField("gpu_model", T.StringType()), T.StructField("price_per_hr_usd", T.DoubleType()),
    T.StructField("evidence", T.StringType()), T.StructField("source", T.StringType()), T.StructField("notes", T.StringType()),
])


def build_dims(spark: SparkSession) -> dict[str, DataFrame]:
    return {
        "dim_coldstart_series": read_seed(spark, "coldstart_series", SEED_SERIES),
        "dim_gpu_label": read_seed(spark, "gpu_labels", SEED_GPU),
        "dim_coldstart_run_notes": read_seed(spark, "coldstart_run_notes", SEED_RUN_NOTES),
    }


# --------------------------------------------------------------------------------------------------
# cold-start requests: emberserve series + Pulse coldstart.py rows → one table
# --------------------------------------------------------------------------------------------------

REQUEST_JSON = T.StructType([
    T.StructField("status", T.IntegerType()), T.StructField("total_s", T.DoubleType()),
    T.StructField("ok", T.BooleanType()), T.StructField("job_status", T.StringType()),
    T.StructField("delay_ms", T.LongType()), T.StructField("execution_ms", T.LongType()),
    T.StructField("worker_id", T.StringType()), T.StructField("submit_wall", T.DoubleType()),
    T.StructField("cold", T.BooleanType()), T.StructField("error", T.StringType()),
    T.StructField("phases_s", T.MapType(T.StringType(), T.DoubleType())),
    T.StructField("timeline", T.StructType([
        T.StructField("marks", T.MapType(T.StringType(), T.DoubleType())),
        T.StructField("notes", T.MapType(T.StringType(), T.StringType())),
    ])),
])

REQUEST_COLUMNS = [
    "source", "engine", "engine_build", "series_label", "endpoint_id", "run_index", "request_index", "kind",
    "request_ts_utc", "model", "gpu_label", "gpu_model", "gpu_tier", "price_per_hr_usd", "flashboot",
    "weights_mode", "http_status", "job_status", "ok", "wall_ms", "delay_ms", "exec_ms", "worker_id",
    "prompt_tokens", "completion_tokens", "is_flashboot_hit", "request_duration_s", "est_cost_usd",
    "host_state", "run_note", "workers_before_json", "error", "source_file", "source_sha256", "bronze_run_label",
]


def emberserve_requests(spark: SparkSession, fmt: str, dims: dict[str, DataFrame]) -> DataFrame:
    runs = latest_per_file(load_or_empty(spark, fmt, "bronze_coldstart_runs"))
    pairs = F.array(
        F.struct(F.lit("cold").alias("kind"), F.col("cold_json").alias("js")),
        F.struct(F.lit("warm").alias("kind"), F.col("warm_json").alias("js")),
    )
    r = (runs.withColumn("p", F.explode(pairs))
             .withColumn("kind", F.col("p.kind"))
             .withColumn("j", F.from_json(F.col("p.js"), REQUEST_JSON)))
    # emberserve series are keyed to a GPU model; the price lives on the matching gpu_labels seed row
    gpu = dims["dim_gpu_label"].select(F.col("gpu_label").alias("_gl"), F.col("tier").alias("gpu_tier"),
                                       "price_per_hr_usd")
    series = dims["dim_coldstart_series"].select("series_label", "engine", "engine_build",
                                                  F.col("model").alias("series_model"), "gpu_model",
                                                  "flashboot", "weights_mode")
    notes = dims["dim_coldstart_run_notes"].select(F.col("series_label").alias("_sl"), F.col("run_index").alias("_ri"),
                                                    F.col("host_state").alias("_hs"), F.col("note").alias("run_note"))
    out = (r.withColumnRenamed("label", "series_label")
             .join(series, "series_label", "left")
             .join(gpu, F.col("gpu_model") == F.col("_gl"), "left")
             .join(notes, (F.col("series_label") == F.col("_sl")) & (F.col("run_index") == F.col("_ri")), "left")
             .select(
                 F.lit("emberserve_results").alias("source"),
                 F.coalesce("engine", F.lit("emberserve")).alias("engine"),
                 "engine_build", "series_label",
                 F.col("endpoint").alias("endpoint_id"),
                 F.col("run_index").cast("int"),
                 F.lit(None).cast("int").alias("request_index"),
                 "kind",
                 F.to_timestamp(F.col("j.submit_wall")).alias("request_ts_utc"),
                 F.col("series_model").alias("model"),
                 F.col("gpu_model").alias("gpu_label"), "gpu_model", "gpu_tier", "price_per_hr_usd",
                 F.coalesce("flashboot", F.lit("unknown")).alias("flashboot"),
                 "weights_mode",
                 F.col("j.status").alias("http_status"), F.col("j.job_status").alias("job_status"),
                 F.coalesce(F.col("j.ok"), F.lit(False)).alias("ok"),
                 (F.col("j.total_s") * 1000).alias("wall_ms"),
                 F.col("j.delay_ms").alias("delay_ms"), F.col("j.execution_ms").alias("exec_ms"),
                 F.col("j.worker_id").alias("worker_id"),
                 F.lit(None).cast("long").alias("prompt_tokens"), F.lit(None).cast("long").alias("completion_tokens"),
                 F.coalesce(F.col("_hs"), F.lit("unknown")).alias("host_state"), "run_note",
                 F.col("health_before_json").alias("workers_before_json"),
                 F.col("j.error").alias("error"),
                 "source_file", "source_sha256", F.col("run_label").alias("bronze_run_label"),
             ))
    return out


def pulse_requests(spark: SparkSession, fmt: str, dims: dict[str, DataFrame]) -> DataFrame:
    b = latest_per_file(load_or_empty(spark, fmt, "bronze_pulse_coldstart_requests"))
    # three files; results_v0.csv and bench/logs/results_runs1-3.csv are byte-identical copies of runs 1-3
    prio = F.when(F.col("source_file") == "pulse/results.csv", 0).otherwise(1)
    key = ["ts_utc", "endpoint_id", "kind", "cycle", "req", "delay_ms", "exec_ms"]
    b = (b.withColumn("_rn", F.row_number().over(Window.partitionBy(*key).orderBy(prio, "source_file")))
          .where(F.col("_rn") == 1).drop("_rn"))
    gpu = dims["dim_gpu_label"].select(F.col("gpu_label").alias("_gl"), F.col("tier").alias("gpu_tier"),
                                       "gpu_model", "price_per_hr_usd")
    is_num = F.col("status").rlike(r"^\d+$")
    out = (b.join(gpu, F.col("gpu") == F.col("_gl"), "left")
            .select(
                F.lit("pulse_coldstart").alias("source"),
                F.lit("worker-vllm").alias("engine"),
                F.lit(None).cast("string").alias("engine_build"),
                F.lit(None).cast("string").alias("series_label"),
                "endpoint_id",
                F.col("cycle").cast("int").alias("run_index"),
                F.col("req").cast("int").alias("request_index"),
                "kind",
                F.to_timestamp("ts_utc").alias("request_ts_utc"),
                canonical_model(F.col("model")).alias("model"),
                F.col("gpu").alias("gpu_label"), "gpu_model", "gpu_tier", "price_per_hr_usd",
                F.lit("unknown").alias("flashboot"),
                F.when(F.col("gpu").contains("vol"), "volume").otherwise("fetched").alias("weights_mode"),
                F.when(is_num, F.col("status").cast("int")).alias("http_status"),
                F.when(~is_num, F.col("status")).alias("job_status"),
                (F.col("status") == "COMPLETED").alias("ok"),
                F.col("wall_ms").cast("double").alias("wall_ms"),
                F.col("delay_ms").cast("long").alias("delay_ms"), F.col("exec_ms").cast("long").alias("exec_ms"),
                F.lit(None).cast("string").alias("worker_id"),
                F.col("prompt_tokens").cast("long"), F.col("completion_tokens").cast("long"),
                F.lit("unknown").alias("host_state"), F.lit(None).cast("string").alias("run_note"),
                F.when(F.col("workers_before") != "", F.col("workers_before")).alias("workers_before_json"),
                F.when(F.col("error") != "", F.col("error")).alias("error"),
                "source_file", "source_sha256", F.col("run_label").alias("bronze_run_label"),
            ))
    return out


def build_coldstart_requests(spark: SparkSession, fmt: str, dims: dict[str, DataFrame]) -> DataFrame:
    e = emberserve_requests(spark, fmt, dims)
    p = pulse_requests(spark, fmt, dims)
    df = e.unionByName(p)
    # request_duration_s is a cost *proxy*, not billed time: Runpod bills worker start, execution and idle
    # phases per worker, which a per-request sum neither bounds from above nor below.
    duration_s = (F.coalesce(F.col("delay_ms"), F.lit(0)) + F.coalesce(F.col("exec_ms"), F.lit(0))) / 1000.0
    return (df.withColumn("is_flashboot_hit",
                          F.when(F.col("kind") == "cold",
                                 F.col("ok") & (F.col("delay_ms") < FLASHBOOT_HIT_MS)))
              .withColumn("request_duration_s", F.when(F.col("ok"), duration_s))
              .withColumn("est_cost_usd", F.col("request_duration_s") / 3600.0 * F.col("price_per_hr_usd"))
              .select(*REQUEST_COLUMNS))


def build_coldstart_phases(spark: SparkSession, fmt: str) -> DataFrame:
    runs = latest_per_file(load_or_empty(spark, fmt, "bronze_coldstart_runs"))
    j = runs.withColumn("j", F.from_json("cold_json", REQUEST_JSON))
    phases = (j.where(F.col("j.phases_s").isNotNull())
               .select(F.col("label").alias("series_label"), F.col("endpoint").alias("endpoint_id"),
                       F.col("run_index").cast("int"), F.col("j.worker_id").alias("worker_id"),
                       F.lit("phase").alias("kind"),
                       F.explode("j.phases_s").alias("name", "value"),
                       "source_file", "source_sha256", F.col("run_label").alias("bronze_run_label")))
    marks = (j.where(F.col("j.timeline.marks").isNotNull())
              .select(F.col("label").alias("series_label"), F.col("endpoint").alias("endpoint_id"),
                      F.col("run_index").cast("int"), F.col("j.worker_id").alias("worker_id"),
                      F.lit("mark").alias("kind"),
                      F.explode("j.timeline.marks").alias("name", "value"),
                      "source_file", "source_sha256", F.col("run_label").alias("bronze_run_label")))
    return (phases.unionByName(marks)
                  .withColumn("seconds", F.when(F.col("kind") == "phase", F.col("value")))
                  .withColumn("mark_ts_utc", F.when(F.col("kind") == "mark", F.to_timestamp(F.col("value"))))
                  .drop("value"))


# --------------------------------------------------------------------------------------------------
# load sweeps
# --------------------------------------------------------------------------------------------------

PCT = T.StructType([T.StructField(k, T.DoubleType()) for k in ("mean", "p50", "p90", "p99")])
SUMMARY = T.StructType([
    T.StructField("num_requests", T.LongType()), T.StructField("completed", T.LongType()),
    T.StructField("failed", T.LongType()), T.StructField("duration_s", T.DoubleType()),
    T.StructField("requests_per_s", T.DoubleType()), T.StructField("throughput_tok_s", T.DoubleType()),
    T.StructField("total_throughput_tok_s", T.DoubleType()),
    T.StructField("ttft_ms", PCT), T.StructField("tpot_ms", PCT), T.StructField("e2e_ms", PCT),
    T.StructField("prompt_tokens", T.LongType()), T.StructField("output_tokens", T.LongType()),
])
TRACE = T.StructType([
    T.StructField("n", T.LongType()), T.StructField("prompt_mean", T.DoubleType()),
    T.StructField("prompt_p50", T.DoubleType()), T.StructField("output_mean", T.DoubleType()),
    T.StructField("output_p50", T.DoubleType()), T.StructField("span_s", T.DoubleType()),
    T.StructField("source", T.StringType()),
])
ARGS = T.StructType([
    T.StructField("client_procs", T.IntegerType()), T.StructField("max_concurrency", T.IntegerType()),
    T.StructField("trace_n", T.IntegerType()), T.StructField("max_prompt_len", T.IntegerType()),
    T.StructField("max_output_len", T.IntegerType()), T.StructField("shared_prefix_len", T.IntegerType()),
    T.StructField("seed", T.IntegerType()), T.StructField("warmup", T.BooleanType()),
])
SERVER_LAT = T.StructType([T.StructField(k, T.DoubleType()) for k in ("ttft_ms_mean", "tpot_ms_mean", "e2e_ms_mean")])


def endpoint_from_url(col):
    """regexp_extract returns "" (not null) on no match, so each candidate is nulled before coalesce."""
    def nz(c):
        return F.when(c != "", c)
    return F.coalesce(nz(F.regexp_extract(col, r"/v2/([a-z0-9]+)(?:/|$)", 1)),
                      nz(F.regexp_extract(col, r"https://([a-z0-9]+)\.api\.runpod\.ai", 1)))


def build_sweep_summaries(spark: SparkSession, fmt: str) -> DataFrame:
    b = latest_per_file(load_or_empty(spark, fmt, "bronze_sweep_runs"))
    s = (b.withColumn("s", F.from_json("summary_json", SUMMARY))
          .withColumn("t", F.from_json("trace_json", TRACE))
          .withColumn("a", F.from_json("args_json", ARGS))
          .withColumn("sl", F.from_json("server_latency_json", SERVER_LAT)))
    cols = [
        "system", F.col("model").alias("served_model"),
        endpoint_from_url(F.col("base_url")).alias("endpoint_id"),
        F.when(F.col("base_url").contains("/v2/"), "queue").otherwise("load_balancer").alias("endpoint_mode"),
        F.col("run_index").cast("int"),
        # null request_rate is the unbounded ("inf") run: every request sent at t=0
        F.coalesce(F.col("request_rate"), F.lit(float("inf"))).alias("request_rate"),
        F.col("request_rate").isNull().alias("is_unbounded"),
        F.col("a.max_concurrency").alias("max_concurrency"), F.col("a.client_procs").alias("client_procs"),
        "wall_s", F.col("s.num_requests").alias("num_requests"), F.col("s.completed").alias("completed"),
        F.col("s.failed").alias("failed"), F.col("s.duration_s").alias("duration_s"),
        F.col("s.requests_per_s").alias("requests_per_s"), F.col("s.throughput_tok_s").alias("output_tok_s"),
        F.col("s.total_throughput_tok_s").alias("total_tok_s"),
    ]
    for m in ("ttft_ms", "tpot_ms", "e2e_ms"):
        for k in ("mean", "p50", "p90", "p99"):
            cols.append(F.col(f"s.{m}.{k}").alias(f"{m}_{k}"))
    cols += [
        F.col("s.prompt_tokens").alias("prompt_tokens"), F.col("s.output_tokens").alias("output_tokens"),
        F.col("t.n").alias("trace_n"), F.col("t.prompt_mean").alias("trace_prompt_mean"),
        F.col("t.output_mean").alias("trace_output_mean"), F.col("t.source").alias("trace_source"),
        F.col("sl.ttft_ms_mean").alias("server_ttft_ms_mean"), F.col("sl.tpot_ms_mean").alias("server_tpot_ms_mean"),
        F.col("sl.e2e_ms_mean").alias("server_e2e_ms_mean"),
        "n_records", "source_file", "source_sha256", F.col("run_label").alias("bronze_run_label"),
    ]
    return s.select(*cols)


def build_sweep_requests(spark: SparkSession, fmt: str) -> DataFrame:
    b = latest_per_file(load_or_empty(spark, fmt, "bronze_sweep_records"))
    w = Window.partitionBy("source_file", "run_index")
    return (b.withColumn("request_rate", F.coalesce(F.col("request_rate"), F.lit(float("inf"))))
             .withColumn("arrival_offset_s", F.col("arrival_s") - F.min("arrival_s").over(w))
             .withColumn("ttft_ms", F.when(F.col("success"), (F.col("first_token_s") - F.col("arrival_s")) * 1000))
             .withColumn("e2e_ms", F.when(F.col("success"), (F.col("finish_s") - F.col("arrival_s")) * 1000))
             .withColumn("tpot_ms", F.when(F.col("success") & (F.col("output_tokens") > 1),
                                           (F.col("finish_s") - F.col("first_token_s")) * 1000 / (F.col("output_tokens") - 1)))
             .select("system", F.col("run_index").cast("int"), "request_rate", "request_id", "arrival_offset_s",
                     "prompt_tokens", "output_tokens", "success", "error", "ttft_ms", "e2e_ms", "tpot_ms",
                     "source_file", "source_sha256", F.col("run_label").alias("bronze_run_label")))


# --------------------------------------------------------------------------------------------------
# worker logs: three timestamp formats, one event table
# --------------------------------------------------------------------------------------------------

RX_CONSOLE = r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) ([A-Z][a-z]{2} \d{2} \d{4} \d{2}:\d{2}:\d{2}) GMT([+-]\d{4}) \([^)]*\) ?(.*)$"
RX_ISO = r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3})\d*Z ?(.*)$"
RX_PIPE = r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \| (\w+) \| (\w+) \| ?(.*)$"
RX_VLLM = r"^\((\w+) pid=(\d+)\)\s*(.*)$"
SDK_JSON = T.StructType([T.StructField("requestId", T.StringType()), T.StructField("message", T.StringType()),
                         T.StructField("level", T.StringType())])


def build_worker_log_events(spark: SparkSession, fmt: str) -> DataFrame:
    b = latest_per_file(load_or_empty(spark, fmt, "bronze_worker_log_lines"))
    line = F.col("raw_line")
    fmt_col = (F.when(line.rlike(RX_CONSOLE), "console")
                .when(line.rlike(RX_ISO), "iso")
                .when(line.rlike(RX_PIPE), "pipe")
                .otherwise("none"))
    console_ts = F.to_timestamp(F.concat_ws(" ", F.regexp_extract(line, RX_CONSOLE, 1), F.regexp_extract(line, RX_CONSOLE, 2)),
                                "MMM dd yyyy HH:mm:ss xx")
    iso_ts = F.to_timestamp(F.regexp_extract(line, RX_ISO, 1), "yyyy-MM-dd'T'HH:mm:ss.SSS")
    pipe_ts = F.to_utc_timestamp(F.to_timestamp(F.regexp_extract(line, RX_PIPE, 1), "yyyy-MM-dd HH:mm:ss.SSS"), CONSOLE_LOG_TZ)
    payload = (F.when(F.col("ts_format") == "console", F.regexp_extract(line, RX_CONSOLE, 3))
                .when(F.col("ts_format") == "iso", F.regexp_extract(line, RX_ISO, 2))
                .when(F.col("ts_format") == "pipe", F.regexp_extract(line, RX_PIPE, 4))
                .otherwise(line))
    df = (b.withColumn("ts_format", fmt_col)
           .withColumn("ts_utc", F.when(F.col("ts_format") == "console", console_ts)
                                  .when(F.col("ts_format") == "iso", iso_ts)
                                  .when(F.col("ts_format") == "pipe", pipe_ts))
           .withColumn("worker_id", F.when(F.col("ts_format") == "pipe", F.regexp_extract(line, RX_PIPE, 3)))
           .withColumn("console_level", F.when(F.col("ts_format") == "pipe", F.regexp_extract(line, RX_PIPE, 2)))
           .withColumn("payload", payload))
    p = F.col("payload")
    # The endpoint-logs export (pipe format) strips the "(Role pid=N)" prefix and the SDK's JSON wrapper, so
    # the same vLLM / SDK lines appear in two spellings; both land in the same event_kind.
    is_sdk_json = p.rlike(r'^\{"requestId"')
    is_sdk_text = p.rlike(r"^(Jobs in (queue|progress): \d+|Finished running generator\.|Finished\.|Running \d+ fitness check|"
                          r"GPU binary test|Memory check|Disk space check|--- Starting Serverless Worker)")
    is_vllm_bare = p.rlike(r"^(INFO|WARNING|ERROR|DEBUG|CRITICAL)[: ]+\d\d-\d\d \d\d:\d\d:\d\d \[")
    kind = (F.when(is_sdk_json | is_sdk_text, "runpod_sdk")
             .when(p.rlike(RX_VLLM) | is_vllm_bare, "vllm")
             .when(p.rlike(r"\d+%\|") | p.rlike(r"^Loading safetensors checkpoint shards:"), "progress")
             .when(p.rlike(r"INFO httpx:"), "httpx")
             .when(p.rlike(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ (INFO|WARNING|ERROR) root:"), "wrapper")
             .when(p == "", "blank")
             .otherwise("other"))
    rest = F.when(p.rlike(RX_VLLM), F.regexp_extract(p, RX_VLLM, 3)).otherwise(p)
    vllm_level = F.regexp_extract(rest, r"^(INFO|WARNING|ERROR|DEBUG|CRITICAL)", 1)
    vllm_msg = F.regexp_replace(rest, r"^(INFO|WARNING|ERROR|DEBUG|CRITICAL):?\s*(\d\d-\d\d \d\d:\d\d:\d\d \[[^\]]+\]\s*)?", "")
    wrapper_msg = F.regexp_replace(p, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ (INFO|WARNING|ERROR) root:\s*", "")
    sdk = F.from_json(p, SDK_JSON)
    has_role = p.rlike(RX_VLLM)
    df = (df.withColumn("event_kind", kind)
            .withColumn("process_role", F.when(has_role, F.regexp_extract(p, RX_VLLM, 1)))
            .withColumn("pid", F.when(has_role, F.regexp_extract(p, RX_VLLM, 2).cast("int")))
            .withColumn("level", F.when(F.col("event_kind") == "vllm", F.when(vllm_level != "", vllm_level))
                                  .when(is_sdk_json, sdk["level"])
                                  .when(F.col("event_kind") == "wrapper", F.regexp_extract(p, r" (INFO|WARNING|ERROR) root:", 1))
                                  .otherwise(F.upper(F.col("console_level"))))
            .withColumn("request_id", F.when(is_sdk_json, sdk["requestId"]))
            .withColumn("message", F.when(F.col("event_kind") == "vllm", vllm_msg)
                                    .when(is_sdk_json, sdk["message"])
                                    .when(F.col("event_kind") == "wrapper", wrapper_msg)
                                    .otherwise(p)))
    return df.select("source_file", "source_sha256", "line_no", "ts_utc", "ts_format", "worker_id", "event_kind", "process_role",
                     "pid", "level", "request_id", "message", "payload", F.col("run_label").alias("bronze_run_label"))


# --------------------------------------------------------------------------------------------------
# scoring job (Pulse quality.py)
# --------------------------------------------------------------------------------------------------

def build_scoring_requests(spark: SparkSession, fmt: str) -> DataFrame:
    b = latest_per_file(load_or_empty(spark, fmt, "bronze_pulse_quality_requests"))
    nz = lambda c: F.when(F.col(c) != "", F.col(c))   # Pulse writes empty strings for missing values
    return b.select(
        F.to_timestamp("ts_utc").alias("request_ts_utc"), "backend", canonical_model(F.col("model")).alias("model"),
        F.col("model").alias("model_raw"), nz("label").alias("label"), "host", nz("gpu").alias("gpu_model"),
        "batch_id", F.col("concurrency").cast("int"), F.col("article_id").cast("long"), "domain",
        F.col("wall_ms").cast("long"), F.col("prompt_tokens").cast("long"), F.col("completion_tokens").cast("long"),
        nz("finish_reason").alias("finish_reason"), F.col("score").cast("int"), nz("reason").alias("reason"),
        (F.col("parse_ok") == "1").alias("parse_ok"), nz("error").alias("error"),
        "price_unit", nz("rate_in").cast("double").alias("rate_in_usd_per_m"),
        nz("rate_out").cast("double").alias("rate_out_usd_per_m"), nz("rate_hr").cast("double").alias("rate_usd_per_hr"),
        "rate_source", nz("est_cost_usd").cast("double").alias("est_cost_usd"), "fixture_sha",
        F.col("extra").alias("extra_json"), "source_file", "source_sha256", F.col("run_label").alias("bronze_run_label"),
    )


def build_scoring_batches(spark: SparkSession, fmt: str) -> DataFrame:
    b = latest_per_file(load_or_empty(spark, fmt, "bronze_pulse_quality_batches"))
    nz = lambda c: F.when(F.col(c) != "", F.col(c))
    return b.select(
        "batch_id", F.to_timestamp("ts_utc").alias("batch_ts_utc"), "backend",
        canonical_model(F.col("model")).alias("model"), F.col("model").alias("model_raw"), nz("label").alias("label"),
        "host", nz("gpu").alias("gpu_model"), nz("worker_id").alias("worker_id"), F.col("concurrency").cast("int"),
        F.col("n").cast("int"), F.col("ok").cast("int").alias("n_ok"), F.col("parse_ok").cast("int").alias("n_parse_ok"),
        F.col("wall_ms").cast("long"), nz("served_model").alias("served_model"),
        nz("workers_before").alias("workers_before_json"), "price_unit",
        nz("rate_in").cast("double").alias("rate_in_usd_per_m"), nz("rate_out").cast("double").alias("rate_out_usd_per_m"),
        nz("rate_hr").cast("double").alias("rate_usd_per_hr"), "rate_source",
        nz("est_cost_usd").cast("double").alias("est_cost_usd"), "fixture_sha", nz("note").alias("note"),
        "source_file", "source_sha256", F.col("run_label").alias("bronze_run_label"),
    )


# --------------------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--format", default="delta", choices=["delta", "parquet"])
    args = ap.parse_args(argv)
    spark = get_spark(args.format, app="silver-build")
    manifest = read_manifest(LANDING_DIR)
    set_snapshot(spark, manifest)
    assert_snapshot_in_bronze(spark, args.format, manifest)

    dims = build_dims(spark)
    builders = {
        "dim_coldstart_series": lambda: dims["dim_coldstart_series"],
        "dim_gpu_label": lambda: dims["dim_gpu_label"],
        "dim_coldstart_run_notes": lambda: dims["dim_coldstart_run_notes"],
        "silver_coldstart_requests": lambda: build_coldstart_requests(spark, args.format, dims),
        "silver_coldstart_phases": lambda: build_coldstart_phases(spark, args.format),
        "silver_sweep_summaries": lambda: build_sweep_summaries(spark, args.format),
        "silver_sweep_requests": lambda: build_sweep_requests(spark, args.format),
        "silver_worker_log_events": lambda: build_worker_log_events(spark, args.format),
        "silver_scoring_requests": lambda: build_scoring_requests(spark, args.format),
        "silver_scoring_batches": lambda: build_scoring_batches(spark, args.format),
    }
    print(f"silver format={args.format} built_at={BUILT_AT.isoformat()}")
    for name in SILVER_TABLES:
        n = write(builders[name](), args.format, name)
        print(f"  {name:<30} {n:>7,} rows")

    # soft checks that print rather than fail: unmatched seeds mean a new GPU label or series appeared
    req = spark.read.format(args.format).load(str(table_path("silver_coldstart_requests")))
    missing_gpu = [r[0] for r in req.where(F.col("gpu_tier").isNull()).select("gpu_label").distinct().collect()]
    missing_series = [r[0] for r in req.where((F.col("source") == "emberserve_results") & F.col("model").isNull())
                                        .select("series_label").distinct().collect()]
    if missing_gpu:
        print(f"  note: gpu labels without a seeds/gpu_labels.csv row: {missing_gpu}")
    if missing_series:
        print(f"  note: series without a seeds/coldstart_series.csv row: {missing_series}")
    ev = spark.read.format(args.format).load(str(table_path("silver_worker_log_events")))
    unparsed = ev.where(F.col("ts_utc").isNull()).count()
    print(f"  worker-log lines without a parsed timestamp: {unparsed:,} of {ev.count():,}")
    spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
