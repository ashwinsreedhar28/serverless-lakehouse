"""One SparkSession builder for every step.

FORMAT=delta (default) registers the Delta Lake extension; the Delta JVM jars are resolved by Spark
from Maven Central on first start (~10 MB into ~/.ivy2). FORMAT=parquet skips that, for sandboxes
with no Maven access. The storage format is the only thing that changes; every read/write in this
repo goes through `format(fmt)`, so the two modes exercise the same code.
"""

from __future__ import annotations

import os
import sys

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T


def get_spark(fmt: str = "delta", app: str = "serverless-lakehouse") -> SparkSession:
    # Python workers must run the same interpreter as the driver. Left unset, Spark launches whatever `python3`
    # is first on PATH, which on a machine with a newer system Python than the venv fails with
    # "Python in worker has different version than that in driver".
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
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


def timestamps_as_utc_strings(df: DataFrame) -> DataFrame:
    """Render every TimestampType column as an ISO-8601 UTC string on the JVM side.

    PySpark's collect() hands timestamps to the driver as naive datetimes in the driver's *local* zone; a
    laptop in US-Eastern would then serialise them four hours behind UTC with no offset. The session zone is
    UTC, so date_format produces the right instant and the 'Z' makes it explicit.
    """
    for f in df.schema.fields:
        if isinstance(f.dataType, T.TimestampType):
            df = df.withColumn(f.name, F.date_format(F.col(f.name), "yyyy-MM-dd'T'HH:mm:ss'Z'"))
    return df
