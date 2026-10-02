"""One SparkSession builder for every step.

FORMAT=delta (default) registers the Delta Lake extension; the Delta JVM jars are resolved by Spark
from Maven Central on first start (~10 MB into ~/.ivy2). FORMAT=parquet skips that, for sandboxes
with no Maven access. The storage format is the only thing that changes; every read/write in this
repo goes through `format(fmt)`, so the two modes exercise the same code.
"""

from __future__ import annotations

from pyspark.sql import SparkSession


def get_spark(fmt: str = "delta", app: str = "serverless-lakehouse") -> SparkSession:
    b = (
        SparkSession.builder.master("local[*]")
        .appName(app)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "8")   # tables are KB–MB; 200 shuffle partitions is pure overhead
        .config("spark.ui.enabled", "false")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
    )
    if fmt == "delta":
        from delta import configure_spark_with_delta_pip  # imported lazily so parquet mode needs no delta jars

        b = (
            b.config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
             .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        )
        spark = configure_spark_with_delta_pip(b).getOrCreate()
    elif fmt == "parquet":
        spark = b.getOrCreate()
    else:
        raise SystemExit(f"unknown format {fmt!r} (delta|parquet)")
    spark.sparkContext.setLogLevel("ERROR")
    return spark
