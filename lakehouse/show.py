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
        # date_format runs on the JVM in the session time zone (UTC); collecting a raw timestamp would
        # have PySpark render it in the driver's local zone.
        agg = df.agg(F.count("*").alias("rows"),
                     F.countDistinct("source_file").alias("files"),
                     F.countDistinct("run_label").alias("labels"),
                     F.date_format(F.max("ingested_at"), "yyyy-MM-dd HH:mm:ss").alias("latest")).first()
        print(f"{t:<34} {agg['rows']:>8,} {agg['files']:>6} {agg['labels']:>10}  {agg['latest']}")

    log = load_table(spark, args.format, "bronze_ingest_log")
    if log is not None:
        print("\nruns:")
        runs = (log.groupBy("run_label", "ingested_at").agg(F.sum("rows").alias("rows"), F.count("*").alias("appends"))
                   .orderBy("ingested_at")
                   .withColumn("at", F.date_format("ingested_at", "yyyy-MM-dd HH:mm:ss")).collect())
        for r in runs:
            print(f"  {r['run_label']:<28} {r['at']} UTC  {r['rows']:>7,} rows in {r['appends']} appends")
    spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
