"""Gold: silver → the tables the dashboard reads. Small, aggregated, one question per table.

    python -m lakehouse.gold [--format delta|parquet]

Rebuilt from scratch every run (overwrite), like silver. Only `ok` requests enter latency and cost
aggregates; failures are counted separately where they matter. Percentiles use percentile_approx, which on
tables this size (tens to thousands of rows) is exact.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql import types as T

from .config import FLASHBOOT_HIT_MS, GOLD_TABLES, table_path
from .spark import get_spark

BUILT_AT = datetime.now(timezone.utc).replace(microsecond=0)


def load(spark: SparkSession, fmt: str, name: str) -> DataFrame:
    return spark.read.format(fmt).load(str(table_path(name)))


def write(df: DataFrame, fmt: str, name: str) -> int:
    df = df.withColumn("gold_built_at", F.lit(BUILT_AT).cast(T.TimestampType()))
    w = df.write.format(fmt).mode("overwrite")
    if fmt == "delta":
        w = w.option("overwriteSchema", "true")
    w.save(str(table_path(name)))
    return df.count()


def pct(col: str, q: float, alias: str):
    return F.percentile_approx(col, q).alias(alias)


# --------------------------------------------------------------------------------------------------

def coldstart_by_gpu_image(req: DataFrame) -> DataFrame:
    ok = req.where("ok")
    g = ["engine", "model", "gpu_model", "gpu_tier", "weights_mode", "flashboot", "kind"]
    return (ok.groupBy(*g)
              .agg(F.count("*").alias("n"),
                   F.sum(F.col("is_flashboot_hit").cast("int")).alias("n_flashboot_hits"),
                   pct("delay_ms", 0.5, "delay_ms_p50"), pct("delay_ms", 0.9, "delay_ms_p90"),
                   F.min("delay_ms").alias("delay_ms_min"), F.max("delay_ms").alias("delay_ms_max"),
                   pct("exec_ms", 0.5, "exec_ms_p50"),
                   F.percentile_approx(F.when(~F.coalesce(F.col("is_flashboot_hit"), F.lit(False)), F.col("delay_ms")), 0.5)
                    .alias("full_boot_delay_ms_p50"),
                   pct("est_cost_usd", 0.5, "est_cost_usd_p50"),
                   F.countDistinct("endpoint_id").alias("n_endpoints"),
                   F.countDistinct("worker_id").alias("n_workers_seen"))
              .withColumn("gpu_model", F.coalesce("gpu_model", F.lit("not captured")))
              .orderBy("engine", "model", "gpu_model", "weights_mode", "flashboot", "kind"))


def flashboot_hit_rate(req: DataFrame) -> DataFrame:
    cold = req.where("ok and kind = 'cold'")
    hit = F.col("is_flashboot_hit")
    return (cold.groupBy("engine", "model", "endpoint_id", F.col("flashboot").alias("flashboot_setting"))
                .agg(F.count("*").alias("n_cold"),
                     F.sum(hit.cast("int")).alias("n_hits"),
                     F.percentile_approx(F.when(hit, F.col("delay_ms")), 0.5).alias("hit_delay_ms_p50"),
                     F.percentile_approx(F.when(~hit, F.col("delay_ms")), 0.5).alias("miss_delay_ms_p50"),
                     F.min("request_ts_utc").alias("first_request_utc"), F.max("request_ts_utc").alias("last_request_utc"))
                .withColumn("hit_rate", F.round(F.col("n_hits") / F.col("n_cold"), 3))
                .withColumn("hit_threshold_ms", F.lit(FLASHBOOT_HIT_MS))
                .orderBy("engine", "model", "endpoint_id"))


def engine_comparison(req: DataFrame) -> DataFrame:
    """Same GPU, same model: what does each engine cost you on a cold start, and what does warm look like?

    Two kinds of row, told apart by `scope`: `pooled` aggregates every full boot of that engine × weights mode;
    one row per `cohort` splits them by host state and data era, because a pooled median mixes a fresh host that
    had to pull the image, same-night reruns on a warm host, and the Sep 23 Pulse-era runs (worker-vllm 2.27 with
    endpoint rollouts). Quote the pooled number only with the word pooled; the cohort rows reproduce the figures in
    earlier write-ups (the two warm-host worker-vllm samples average 147.5 s).
    """
    same = (req.where("ok and model = 'Qwen3-8B' and gpu_model = 'RTX 4090'")
               .withColumn("cohort", F.when(F.col("host_state") != "unknown", F.col("host_state"))
                                      .when(F.col("source") == "pulse_coldstart", "pulse_sep23_host_unknown")
                                      .otherwise("host_unknown")))
    cold_full = same.where("kind = 'cold' and not coalesce(is_flashboot_hit, false)")
    warm = same.where("kind = 'warm'")

    def agg(df_cold, df_warm, keys, scope):
        c = (df_cold.groupBy(*keys)
                    .agg(F.count("*").alias("n_full_boots"),
                         pct("delay_ms", 0.5, "cold_delay_ms_p50"), F.round(F.avg("delay_ms")).cast("long").alias("cold_delay_ms_mean"),
                         F.min("delay_ms").alias("cold_delay_ms_min"), F.max("delay_ms").alias("cold_delay_ms_max"),
                         pct("exec_ms", 0.5, "cold_exec_ms_p50"), pct("est_cost_usd", 0.5, "cold_est_cost_usd_p50"),
                         F.array_sort(F.collect_set("series_label")).alias("series"),
                         F.array_sort(F.collect_set(F.date_format("request_ts_utc", "yyyy-MM-dd"))).alias("dates")))
        w = (df_warm.groupBy(*keys)
                    .agg(F.count("*").alias("n_warm"), pct("delay_ms", 0.5, "warm_delay_ms_p50"), pct("exec_ms", 0.5, "warm_exec_ms_p50")))
        out = c.join(w, keys, "full").withColumn("scope", F.lit(scope))
        if "cohort" not in keys:
            out = out.withColumn("cohort", F.lit("all runs (pooled)"))
        return out

    pooled = agg(cold_full, warm, ["engine", "weights_mode"], "pooled")
    cohorts = agg(cold_full, warm, ["engine", "weights_mode", "cohort"], "cohort")
    cols = ["engine", "weights_mode", "scope", "cohort", "n_full_boots", "cold_delay_ms_p50", "cold_delay_ms_mean",
            "cold_delay_ms_min", "cold_delay_ms_max", "cold_exec_ms_p50", "cold_est_cost_usd_p50", "n_warm",
            "warm_delay_ms_p50", "warm_exec_ms_p50", "series", "dates"]
    return (pooled.select(*cols).unionByName(cohorts.select(*cols))
                  .where(F.col("n_full_boots").isNotNull())   # a cohort with only warm requests says nothing about cold boots
                  .orderBy("engine", "weights_mode", F.when(F.col("scope") == "pooled", 0).otherwise(1), "cohort"))


def worker_boot_phases(ev: DataFrame) -> DataFrame:
    """worker-vllm's own account of a boot, from the log lines vLLM prints while starting."""
    m = F.col("message")
    # The wrapper's "Starting vLLM: vllm serve ..." opens a boot; vLLM's own "Starting vLLM server on http://..."
    # comes ~2 min later and must not. A console export can interleave several workers, so segment per worker.
    is_start = m.startswith("Starting vLLM: ")
    wk = F.coalesce(F.col("worker_id"), F.lit(""))
    w_file = Window.partitionBy("source_file", wk).orderBy("line_no").rowsBetween(Window.unboundedPreceding, 0)
    e = (ev.withColumn("boot_index", F.sum(is_start.cast("int")).over(w_file))
           .where(F.col("boot_index") > 0)
           .withColumn("_wk", wk))
    num = lambda rx: F.regexp_extract(m, rx, 1).cast("double")
    g = e.groupBy("source_file", "_wk", "boot_index").agg(
        F.first(F.when(F.col("worker_id").isNotNull(), F.col("worker_id")), ignorenulls=True).alias("worker_id"),
        F.first("ts_format").alias("ts_format"),
        F.min(F.when(is_start, F.col("ts_utc"))).alias("t_start_vllm"),
        F.min(F.when(m.startswith("Loading weights took"), F.col("ts_utc"))).alias("t_weights_loaded"),
        F.min(F.when(m.startswith("Application startup complete"), F.col("ts_utc"))).alias("t_api_ready"),
        F.min(F.when(m.startswith("--- Starting Serverless Worker"), F.col("ts_utc"))).alias("t_sdk_started"),
        F.max(F.when(m.startswith("Loading weights took"), num(r"Loading weights took ([\d.]+) seconds"))).alias("weights_load_s"),
        F.max(F.when(m.startswith("Model loading took"), num(r"Model loading took ([\d.]+) GiB"))).alias("model_gib"),
        F.max(F.when(m.startswith("Model loading took"), num(r"and ([\d.]+) seconds"))).alias("model_load_s"),
        F.max(F.when(m.startswith("torch.compile took"), num(r"torch\.compile took ([\d.]+) s"))).alias("torch_compile_s"),
        F.max(F.when(m.startswith("Graph capturing finished"), num(r"finished in ([\d.]+) secs"))).alias("graph_capture_s"),
        F.max(F.when(m.startswith("init engine"), num(r"took ([\d.]+) s"))).alias("init_engine_s"),
        F.max(F.when(m.startswith("init engine"), num(r"compilation: ([\d.]+) s"))).alias("init_engine_compile_s"),
        F.max(F.when(m.startswith("Available KV cache memory"), num(r"([\d.]+) GiB"))).alias("kv_cache_gib"),
        F.max(F.when(m.startswith("Maximum concurrency"), num(r": ([\d.]+)x"))).alias("max_concurrency_x"),
        F.max(F.when(m.startswith("Initializing a V1 LLM engine"), F.regexp_extract(m, r"\((v[\d.]+)\)", 1))).alias("vllm_version"),
        F.max(F.when(m.startswith("--- Starting Serverless Worker"), F.regexp_extract(m, r"Version ([\d.]+)", 1))).alias("runpod_sdk_version"),
        F.sum(F.when(F.col("event_kind") == "progress", 1).otherwise(0)).alias("n_progress_lines"),
        F.count("*").alias("n_lines"),
    )
    first_job = (e.where(m.startswith("Jobs in queue"))
                  .groupBy("source_file", "_wk", "boot_index").agg(F.min("ts_utc").alias("t_first_job_seen")))
    out = (g.join(first_job, ["source_file", "_wk", "boot_index"], "left")
            .withColumn("start_to_weights_s", F.col("t_weights_loaded").cast("double") - F.col("t_start_vllm").cast("double"))
            .withColumn("start_to_api_ready_s", F.col("t_api_ready").cast("double") - F.col("t_start_vllm").cast("double"))
            .withColumn("api_ready_to_sdk_s", F.col("t_sdk_started").cast("double") - F.col("t_api_ready").cast("double"))
            .withColumn("api_ready_to_first_job_s",
                        F.when(F.col("t_first_job_seen") >= F.col("t_api_ready"),
                               F.col("t_first_job_seen").cast("double") - F.col("t_api_ready").cast("double")))
            .select("source_file", "boot_index", "worker_id", "ts_format", "vllm_version", "runpod_sdk_version",
                    "t_start_vllm", "t_api_ready",
                    "start_to_weights_s", "weights_load_s", "model_gib", "model_load_s", "torch_compile_s",
                    "graph_capture_s", "init_engine_s", "init_engine_compile_s", "start_to_api_ready_s",
                    "api_ready_to_sdk_s", "api_ready_to_first_job_s", "kv_cache_gib", "max_concurrency_x",
                    "n_progress_lines", "n_lines")
            .orderBy("source_file", "boot_index"))
    return out


def coldstart_events(req: DataFrame) -> DataFrame:
    """Event-level projection for the dashboard's dot plot: every successful cold request, one row."""
    return (req.where("ok and kind = 'cold'")
               .select("source", "engine", "model", F.coalesce("gpu_model", F.lit("not captured")).alias("gpu_model"),
                       "gpu_tier", "weights_mode", "flashboot", "host_state", "series_label", "endpoint_id", "run_index",
                       "request_ts_utc", "delay_ms", "exec_ms", "worker_id", "is_flashboot_hit", "est_cost_usd", "source_file")
               .orderBy("engine", "weights_mode", "delay_ms"))


def cost_per_job(req: DataFrame) -> DataFrame:
    priced = req.where("ok and price_per_hr_usd is not null")
    return (priced.groupBy("engine", "model", "gpu_model", "gpu_tier", "weights_mode", "kind", "price_per_hr_usd")
                  .agg(F.count("*").alias("n"), pct("billed_s", 0.5, "billed_s_p50"), pct("billed_s", 0.9, "billed_s_p90"),
                       pct("est_cost_usd", 0.5, "est_cost_usd_p50"), F.round(F.sum("est_cost_usd"), 4).alias("est_cost_usd_total"))
                  .withColumn("gpu_model", F.coalesce("gpu_model", F.lit("not captured")))
                  .withColumn("cost_formula", F.lit("(delay_ms + exec_ms) / 3.6e6 * price_per_hr_usd"))
                  .orderBy("engine", "model", "kind", "gpu_tier"))


def scoring_cost_per_batch(batches: DataFrame, reqs: DataFrame) -> DataFrame:
    per = (reqs.groupBy("batch_id")
               .agg(F.round(F.avg("score"), 3).alias("mean_score"),
                    F.round(F.avg(F.col("parse_ok").cast("int")), 3).alias("parse_ok_rate"),
                    pct("wall_ms", 0.5, "article_wall_ms_p50"), pct("wall_ms", 0.9, "article_wall_ms_p90"),
                    F.sum("prompt_tokens").alias("prompt_tokens"), F.sum("completion_tokens").alias("completion_tokens")))
    return (batches.join(per, "batch_id", "left")
                   .withColumn("wall_s_per_article", F.round(F.col("wall_ms") / 1000.0 / F.col("n"), 3))
                   .withColumn("est_cost_usd_per_1k_articles", F.round(F.col("est_cost_usd") / F.col("n") * 1000, 4))
                   .select("batch_id", "batch_ts_utc", "backend", "model", "label", "gpu_model", "concurrency", "n", "n_ok",
                           "parse_ok_rate", "mean_score", "wall_ms", "wall_s_per_article", "article_wall_ms_p50",
                           "article_wall_ms_p90", "prompt_tokens", "completion_tokens", "price_unit", "rate_in_usd_per_m",
                           "rate_out_usd_per_m", "rate_usd_per_hr", "est_cost_usd", "est_cost_usd_per_1k_articles", "note")
                   .orderBy("batch_ts_utc"))


def sweep_latency(summ: DataFrame, reqs: DataFrame) -> DataFrame:
    rec = (reqs.where("success")
               .groupBy("source_file", "run_index")
               .agg(pct("ttft_ms", 0.5, "rec_ttft_ms_p50"), pct("ttft_ms", 0.99, "rec_ttft_ms_p99"),
                    pct("e2e_ms", 0.99, "rec_e2e_ms_p99"), F.count("*").alias("rec_n_ok")))
    return (summ.join(rec, ["source_file", "run_index"], "left")
                .select("system", "endpoint_id", "endpoint_mode", "served_model", "request_rate", "is_unbounded",
                        "max_concurrency", "num_requests", "completed", "failed", "duration_s", "requests_per_s",
                        "output_tok_s", "total_tok_s", "ttft_ms_p50", "ttft_ms_p99", "tpot_ms_p50", "tpot_ms_p99",
                        "e2e_ms_p50", "e2e_ms_p99", "server_ttft_ms_mean", "server_e2e_ms_mean",
                        "rec_n_ok", "rec_ttft_ms_p50", "rec_ttft_ms_p99", "rec_e2e_ms_p99", "source_file")
                .orderBy("system", "request_rate"))


# --------------------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--format", default="delta", choices=["delta", "parquet"])
    args = ap.parse_args(argv)
    spark = get_spark(args.format, app="gold-build")
    L = lambda n: load(spark, args.format, n)

    req, ev = L("silver_coldstart_requests"), L("silver_worker_log_events")
    builders = {
        "gold_coldstart_by_gpu_image": lambda: coldstart_by_gpu_image(req),
        "gold_flashboot_hit_rate": lambda: flashboot_hit_rate(req),
        "gold_engine_comparison": lambda: engine_comparison(req),
        "gold_worker_boot_phases": lambda: worker_boot_phases(ev),
        "gold_cost_per_job": lambda: cost_per_job(req),
        "gold_scoring_cost_per_batch": lambda: scoring_cost_per_batch(L("silver_scoring_batches"), L("silver_scoring_requests")),
        "gold_sweep_latency": lambda: sweep_latency(L("silver_sweep_summaries"), L("silver_sweep_requests")),
        "gold_coldstart_events": lambda: coldstart_events(req),
    }
    print(f"gold format={args.format} built_at={BUILT_AT.isoformat()}")
    for name in GOLD_TABLES:
        n = write(builders[name](), args.format, name)
        print(f"  {name:<30} {n:>5} rows")
    spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
