"""Print what is in bronze: rows, run_labels, source files and the latest ingest per table.

    python -m lakehouse.show [--format delta|parquet]
"""

from __future__ import annotations

import argparse
import sys

from pyspark.sql import functions as F

from .bronze import load_table
from .config import BRONZE_TABLES
from .spark import get_spark


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--format", default="delta", choices=["delta", "parquet"])
    args = ap.parse_args(argv)
    spark = get_spark(args.format, app="bronze-show")

    print(f"{'table':<34} {'rows':>8} {'files':>6} {'run_labels':>10}  latest_ingested_at (UTC)")
    for t in BRONZE_TABLES:
        df = load_table(spark, args.format, t)
        if df is None:
            print(f"{t:<34} {'-':>8}")
            continue
        agg = df.agg(F.count("*").alias("rows"),
                     F.countDistinct("source_file").alias("files"),
                     F.countDistinct("run_label").alias("labels"),
                     F.max("ingested_at").alias("latest")).first()
        print(f"{t:<34} {agg['rows']:>8,} {agg['files']:>6} {agg['labels']:>10}  {agg['latest']}")

    log = load_table(spark, args.format, "bronze_ingest_log")
    if log is not None:
        print("\nruns:")
        for r in (log.groupBy("run_label", "ingested_at").agg(F.sum("rows").alias("rows"), F.count("*").alias("appends"))
                     .orderBy("ingested_at").collect()):
            print(f"  {r['run_label']:<28} {r['ingested_at']}  {r['rows']:>7,} rows in {r['appends']} appends")
    spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
