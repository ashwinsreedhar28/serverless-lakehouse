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


def table_path(name: str) -> Path:
    return BRONZE_DIR / name
