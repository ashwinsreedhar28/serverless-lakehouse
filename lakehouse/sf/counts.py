"""Expected bronze rows per landed file, counted with plain Python — the same independent reader
`lakehouse.verify` uses, repeated here so the Snowflake backend does not import pyspark.

A landed file feeds one or more bronze tables; this says which, and how many rows each should hold.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

# landing dataset tag (manifest) → bronze table for the CSV datasets (same mapping as lakehouse.bronze)
CSV_TABLE_BY_DATASET = {
    "pulse_coldstart": "bronze_pulse_coldstart_requests",
    "pulse_throughput": "bronze_pulse_throughput_requests",
    "pulse_quality": "bronze_pulse_quality_requests",
    "pulse_quality_batches": "bronze_pulse_quality_batches",
}

# The columns silver depends on; a CSV routed to a table without them is mis-tagged (same lists as lakehouse.bronze).
CSV_KEY_COLUMNS = {
    "bronze_pulse_coldstart_requests": ["ts_utc", "endpoint_id", "gpu", "model", "kind", "cycle", "req", "delay_ms", "exec_ms", "status"],
    "bronze_pulse_throughput_requests": ["ts_utc", "endpoint_id", "gpu", "model", "label", "n", "concurrency", "req", "delay_ms", "status"],
    "bronze_pulse_quality_requests": ["ts_utc", "backend", "model", "label", "batch_id", "article_id", "wall_ms", "score", "parse_ok"],
    "bronze_pulse_quality_batches": ["batch_id", "ts_utc", "backend", "model", "label", "n", "wall_ms", "est_cost_usd"],
}

JSON_DATASETS = ("coldstart_series", "sweep")


def expected_rows(path: Path, dataset: str) -> dict[str, int]:
    """{table: rows} that this one landed file should contribute. JSON documents also land whole in bronze_raw_json."""
    if dataset == "coldstart_series":
        d = json.loads(path.read_text(encoding="utf-8"))
        return {"bronze_raw_json": 1, "bronze_coldstart_series": 1, "bronze_coldstart_runs": len(d.get("runs", []))}
    if dataset == "sweep":
        d = json.loads(path.read_text(encoding="utf-8"))
        runs = d.get("runs", [])
        out = {"bronze_raw_json": 1, "bronze_sweep_runs": len(runs)}
        n_rec = sum(len(r.get("records") or []) for r in runs)
        if n_rec:
            out["bronze_sweep_records"] = n_rec
        return out
    if dataset == "worker_log":
        return {"bronze_worker_log_lines": len(path.read_text(encoding="utf-8").splitlines())}
    if dataset in CSV_TABLE_BY_DATASET:
        with path.open(newline="", encoding="utf-8") as f:
            n = sum(1 for _ in csv.DictReader(f))
        return {CSV_TABLE_BY_DATASET[dataset]: n}
    raise ValueError(dataset)


def csv_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as f:
        return next(csv.reader(f))
