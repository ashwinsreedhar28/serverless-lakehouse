"""Render the gold tables to docs/gold_report.md (and stdout) so a reader without Spark sees the results.

    python -m lakehouse.report [--format delta|parquet] [--out docs/gold_report.md]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from .config import REPO_ROOT, table_path
from .spark import get_spark, timestamps_as_utc_strings

# table → (title, one-line question it answers, columns to show)
VIEWS = {
    "gold_engine_comparison": (
        "emberserve vs worker-vllm — Qwen3-8B on an RTX 4090",
        "Same GPU, same model. `scope=pooled` rows mix every full boot of that engine; the `cohort` rows beneath split "
        "them by host state and data era — quote a pooled median only as pooled. The two warm-host worker-vllm samples "
        "are the pair behind the 147.5 s in the Sep 30 write-up.",
        ["engine", "weights_mode", "scope", "cohort", "n_full_boots", "cold_delay_ms_p50", "cold_delay_ms_mean",
         "cold_delay_ms_min", "cold_delay_ms_max", "cold_est_cost_usd_p50", "n_warm", "warm_exec_ms_p50", "dates"]),
    "gold_worker_boot_phases": (
        "worker-vllm boot anatomy, per worker log",
        "Where do the seconds go between `vllm serve` and 'Application startup complete'?",
        ["source_file", "vllm_version", "graph_mode", "start_to_weights_s", "weights_load_s", "torch_compile_s", "graph_capture_s",
         "init_engine_s", "start_to_api_ready_s", "api_ready_to_first_job_s", "kv_cache_gib"]),
    "gold_flashboot_hit_rate": (
        "Fast cold responses (FlashBoot proxy)",
        "Share of *successful* cold-labelled requests answered under the threshold — a FlashBoot resume or a worker that "
        "was still warm; the data cannot tell them apart.",
        ["engine", "model", "endpoint_id", "flashboot_setting", "n_cold", "n_hits", "hit_rate", "hit_delay_ms_p50",
         "miss_delay_ms_p50"]),
    "gold_coldstart_by_gpu_image": (
        "Cold-start distribution by engine × model × GPU × weights mode × FlashBoot",
        "The headline distribution; `kind` separates the cold request from the warm one that followed it.",
        ["engine", "model", "gpu_model", "weights_mode", "flashboot", "kind", "n", "n_flashboot_hits", "delay_ms_p50",
         "delay_ms_p90", "delay_ms_max", "exec_ms_p50", "est_cost_usd_p50"]),
    "gold_cost_per_job": (
        "Request-duration cost proxy per Serverless request",
        "(delay_ms + exec_ms) / 3.6e6 × $/hr of the tier; only rows whose tier price is known. Not billed time: Runpod bills "
        "worker start, execution and idle per worker, so this is a comparison metric, not an invoice estimate.",
        ["engine", "model", "gpu_model", "gpu_tier", "weights_mode", "kind", "price_per_hr_usd", "n", "request_duration_s_p50",
         "est_cost_usd_p50", "est_cost_usd_total"]),
    "gold_scoring_cost_per_batch": (
        "Scoring job: $ and seconds per article, by backend",
        "The Pulse scoring benchmark: 50 articles per batch; cost as recorded by quality.py from the backend's price table.",
        ["backend", "model", "label", "gpu_model", "concurrency", "n", "wall_s_per_article", "mean_score", "parse_ok_rate",
         "est_cost_usd", "est_cost_usd_per_1k_articles"]),
    "gold_sweep_latency": (
        "Load sweeps on Serverless (emberserve)",
        "TTFT / e2e / throughput per request rate. `inf` = unpaced submission (all 200 requests queued at t=0), capped by "
        "`max_concurrency` where set; systems differ in model size (`7b_` = Qwen2.5-7B, otherwise Qwen2.5-0.5B) and endpoint mode.",
        ["system", "served_model", "endpoint_mode", "request_rate", "max_concurrency", "completed", "failed", "requests_per_s",
         "output_tok_s", "ttft_ms_p50", "ttft_ms_p99", "e2e_ms_p50", "e2e_ms_p99"]),
}


def fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if v != v:  # NaN
            return "NaN"
        if v == float("inf"):
            return "inf"
        return f"{v:,.3f}" if abs(v) < 1 else f"{v:,.1f}" if abs(v) < 1000 else f"{v:,.0f}"
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, (list, tuple)):
        return ", ".join(map(str, v))
    return str(v)


def markdown_table(df: DataFrame, cols: list[str]) -> str:
    cols = [c for c in cols if c in df.columns]
    rows = timestamps_as_utc_strings(df.select(*cols)).collect()
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in rows:
        out.append("| " + " | ".join(fmt(r[c]).replace("|", "\\|") for c in cols) + " |")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--format", default="delta", choices=["delta", "parquet"])
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "docs" / "gold_report.md")
    args = ap.parse_args(argv)
    spark = get_spark(args.format, app="gold-report")

    parts = [f"# Gold report\n\nGenerated by `make report` at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
             f"from the {args.format} tables under `data/lakehouse/gold/`. Every number traces back to a landed file through "
             f"bronze's `source_file`.\n"]
    for name, (title, question, cols) in VIEWS.items():
        df = spark.read.format(args.format).load(str(table_path(name)))
        if "source_file" in cols:
            df = df.withColumn("source_file", F.regexp_replace("source_file", r"^(pulse/bench/logs/|emberserve/results/)", ""))
        parts.append(f"## {title}\n\n`{name}` — {question}\n\n{markdown_table(df, cols)}\n")
    text = "\n".join(parts)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nwrote {args.out.relative_to(REPO_ROOT)}")
    spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
