"""Paths and names shared by every step. Everything is relative to the repo root unless overridden."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The landing zone is the trust boundary: the only step that reads un-redacted source bytes
# writes here; every later step reads only from here. In production this would be an S3 prefix.
LANDING_DIR = Path(os.environ.get("LANDING_DIR", REPO_ROOT / "data" / "landing"))
MANIFEST_PATH = LANDING_DIR / "manifest.json"

# Delta (or parquet) tables live here; never committed, always rebuildable from LANDING_DIR.
LAKEHOUSE_DIR = Path(os.environ.get("LAKEHOUSE_DIR", REPO_ROOT / "data" / "lakehouse"))
BRONZE_DIR = LAKEHOUSE_DIR / "bronze"
SILVER_DIR = LAKEHOUSE_DIR / "silver"
GOLD_DIR = LAKEHOUSE_DIR / "gold"

# Hand-curated dimension seeds (committed CSVs): facts read off the Runpod console or run notes that the
# machine-written sources do not carry (GPU model behind a tier label, FlashBoot setting of a series, $/hr).
SEEDS_DIR = REPO_ROOT / "seeds"

# A "cold" request answered faster than this was served by a FlashBoot resume or a still-warm worker, not a
# full boot. Observed: resumes 0.5–0.9 s; the fastest full boot in the data is 12.6 s.
FLASHBOOT_HIT_MS = 5_000

# Worker logs copied from the Runpod console carry local (laptop) timestamps in this zone.
CONSOLE_LOG_TZ = "America/New_York"

# Table names. Prefix = layer; the rest says what one row is.
BRONZE_TABLES = (
    "bronze_coldstart_series",          # one serverless_coldstart_*.json file
    "bronze_coldstart_runs",            # one cold+warm run inside such a file
    "bronze_sweep_runs",                # one request-rate run inside runpod_serverless_*.json
    "bronze_sweep_records",             # one request inside a sweep run that saved per-request records
    "bronze_worker_log_lines",          # one line of a Runpod worker log
    "bronze_pulse_coldstart_requests",  # one row of Pulse results*.csv (coldstart.py)
    "bronze_pulse_throughput_requests", # one row of Pulse results_throughput.csv (throughput.py)
    "bronze_pulse_quality_requests",    # one row of Pulse bench/quality.csv (quality.py)
    "bronze_pulse_quality_batches",     # one row of Pulse bench/quality_batches.csv
    "bronze_ingest_log",                # one (run_label, table, source_file) append
)


SILVER_TABLES = (
    "dim_coldstart_series",         # seed: one cold-start series → engine, model, GPU, FlashBoot, weights mode
    "dim_gpu_label",                # seed: one Pulse/emberserve GPU label → tier, GPU model, $/hr
    "silver_coldstart_requests",    # one Serverless request (cold or warm) from either source, typed, deduped
    "silver_coldstart_phases",      # one (series, run, phase) from emberserve's startup timeline
    "silver_sweep_summaries",       # one request-rate run of a load sweep, typed
    "silver_sweep_requests",        # one request of a sweep, with ttft/e2e/tpot derived
    "silver_worker_log_events",     # one worker-log line, timestamp parsed, payload classified
    "silver_scoring_requests",      # one scored article, typed
    "silver_scoring_batches",       # one scoring batch, typed
)

GOLD_TABLES = (
    "gold_coldstart_by_gpu_image",  # cold-start distribution per engine × model × GPU × weights mode × FlashBoot
    "gold_flashboot_hit_rate",      # share of cold requests served by a resume, per engine × endpoint × setting
    "gold_engine_comparison",       # emberserve vs worker-vllm on the same GPU and model
    "gold_worker_boot_phases",      # worker-vllm boot anatomy per worker log (weights, compile, graphs, init)
    "gold_cost_per_job",            # estimated $ per Serverless request, per engine × model × GPU × kind
    "gold_scoring_cost_per_batch",  # $ and wall time per 50-article scoring batch, per backend × model
    "gold_sweep_latency",           # ttft/e2e/throughput per system × request rate
)


def table_path(name: str) -> Path:
    if name in BRONZE_TABLES:
        return BRONZE_DIR / name
    if name in SILVER_TABLES:
        return SILVER_DIR / name
    if name in GOLD_TABLES:
        return GOLD_DIR / name
    raise KeyError(name)
