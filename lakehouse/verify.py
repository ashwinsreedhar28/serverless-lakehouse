"""Bronze completeness check: for every landed file, the target table must hold exactly the number of
rows the file contains — computed independently here with plain Python (json / csv / splitlines), not
with Spark, so the check is not grading itself.

    python -m lakehouse.verify [--format delta|parquet]

Exit 0 when every (file, table) pair matches; 1 otherwise. A 2× count means the file was appended
twice (`--force`), which is legal for bronze but worth knowing about.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from pyspark.sql import functions as F

from .bronze import CSV_TABLE_BY_DATASET, load_table
from .config import LANDING_DIR, MANIFEST_PATH
from .spark import get_spark


def expected_rows(path: Path, dataset: str) -> dict[str, int]:
    """{table: rows} that this one landed file should contribute."""
    if dataset == "coldstart_series":
        d = json.loads(path.read_text(encoding="utf-8"))
        return {"bronze_coldstart_series": 1, "bronze_coldstart_runs": len(d.get("runs", []))}
    if dataset == "sweep":
        d = json.loads(path.read_text(encoding="utf-8"))
        runs = d.get("runs", [])
        out = {"bronze_sweep_runs": len(runs)}
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--format", default="delta", choices=["delta", "parquet"])
    ap.add_argument("--landing-dir", type=Path, default=LANDING_DIR)
    args = ap.parse_args(argv)

    manifest = json.loads((args.landing_dir / MANIFEST_PATH.name).read_text(encoding="utf-8"))
    spark = get_spark(args.format, app="bronze-verify")

    # actual rows per (table, source_file, sha) in one pass per table
    actual: dict[tuple[str, str, str], int] = {}
    tables = sorted({t for e in manifest["files"] for t in expected_rows(args.landing_dir / e["landed_relpath"], e["dataset"])})
    for t in tables:
        df = load_table(spark, args.format, t)
        if df is None:
            continue
        for r in df.groupBy("source_file", "source_sha256").agg(F.count("*").alias("n")).collect():
            actual[(t, r["source_file"], r["source_sha256"])] = r["n"]

    bad = 0
    total_expected = total_actual = 0
    for e in manifest["files"]:
        for t, exp in expected_rows(args.landing_dir / e["landed_relpath"], e["dataset"]).items():
            got = actual.get((t, e["landed_relpath"], e["sha256_landed"]), 0)
            total_expected += exp
            total_actual += got
            if got != exp:
                bad += 1
                note = f"appended {got // exp}×" if exp and got % exp == 0 and got > exp else "MISMATCH"
                print(f"  {note:<12} {t:<34} {e['landed_relpath']}: expected {exp}, found {got}")
    spark.stop()
    print(f"verify: {len(manifest['files'])} files, {total_expected:,} expected rows, {total_actual:,} found, "
          f"{bad} mismatching file→table pairs → {'OK' if bad == 0 else 'FAIL'}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
