"""Snowflake backend: the same landing zone, loaded with COPY INTO and modelled with dbt.

`lakehouse/` is the Spark + Delta pipeline; `lakehouse/sf/` is the second backend over the same data/landing/:

    python -m lakehouse.sf.setup                  one-time: run snowflake/setup.sql (warehouse, schemas, stages, formats)
    python -m lakehouse.sf.bronze --run-label …   PUT landing files to @LANDING, COPY INTO bronze, FLATTEN the JSON docs,
                                                  write the ingest ledger, reconcile it
    python -m lakehouse.sf.verify                 row counts per (file, table) vs. plain-Python counts of the landed files
    python -m lakehouse.sf.show                   bronze rows / files / ledger, plus Snowflake's own COPY_HISTORY
    python -m lakehouse.sf.parity                 Snowflake gold vs. the Spark gold export (space/data/gold.json)

Silver and gold are the dbt project in snowflake/dbt/ (`make sf-silver-gold` → dbt seed + dbt build).
Nothing here imports pyspark; nothing in the Spark modules imports this.
"""
