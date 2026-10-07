# Snowflake backend

The same landing zone, bronze → silver → gold on Snowflake: COPY INTO for bronze, dbt for silver and gold, a parity
check against the Spark gold tables. The Spark pipeline in `lakehouse/` is untouched; this is a second backend, and the
main README's "Spark vs Snowflake" section says what each one did for me.

```
snowflake/setup.sql        warehouse (X-Small, auto-suspend 60 s, 20-credit monitor), LAKEHOUSE db, LANDING/BRONZE/SILVER/GOLD
                           schemas, internal stages @LANDING @PARITY @RUNPOD, file formats, LAKEHOUSE_ROLE
lakehouse/sf/              the loader: setup.py, bronze.py (PUT + COPY INTO + FLATTEN + ledger), verify.py, show.py, parity.py
snowflake/dbt/             dbt project: silver + gold models, seeds from ../../seeds, generic + singular tests
snowflake/env.example     credentials template → snowflake/.env (gitignored)
snowflake/logs/            every make sf-* target tees its output here (gitignored)
```

## Setup (once)

1. Trial account at signup.snowflake.com (30 days, $400 of usage; only a running warehouse spends it — this build is a
   few credits). Sign in to Snowsight.
2. Key pair — trial accounts enforce MFA on password logins, which nothing unattended can answer:
   ```bash
   mkdir -p ~/.snowflake && cd ~/.snowflake
   openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out lakehouse_rsa_key.p8 -nocrypt
   openssl rsa -in lakehouse_rsa_key.p8 -pubout -out lakehouse_rsa_key.pub && chmod 600 lakehouse_rsa_key.p8
   grep -v -- '-----' lakehouse_rsa_key.pub | tr -d '\n'; echo       # paste into the ALTER USER below
   ```
   In a Snowsight SQL editor as ACCOUNTADMIN, create a service user for the pipeline (SERVICE-type users are exempt from
   MFA and exist for key-pair auth; a dotted or email-shaped personal user name makes the JWT subject ambiguous):
   ```sql
   CREATE USER LAKEHOUSE_SVC TYPE = SERVICE RSA_PUBLIC_KEY = 'MIIB…' DEFAULT_ROLE = ACCOUNTADMIN;
   GRANT ROLE ACCOUNTADMIN TO USER LAKEHOUSE_SVC;   -- setup.sql needs it once; everything after runs as LAKEHOUSE_ROLE
   DESCRIBE USER LAKEHOUSE_SVC;                     -- RSA_PUBLIC_KEY_FP must equal the local key's fingerprint:
   ```
   `openssl rsa -pubin -in ~/.snowflake/lakehouse_rsa_key.pub -outform DER | openssl dgst -sha256 -binary | openssl enc -base64`
3. `cp snowflake/env.example snowflake/.env`, fill in the account identifier (`<locator>.<region>.<cloud>`, e.g. `ab12345.us-east-2.aws` — the cloud segment is required outside AWS us-west-2)
   and user name.
4. `make sf-setup` — creates `.venv-sf`, runs `snowflake/setup.sql` as ACCOUNTADMIN, grants LAKEHOUSE_ROLE to your user,
   then `dbt debug`.

## Run

```bash
make sf-bronze RUN_LABEL=2026-10-08_initial   # 47 files → @LANDING/<sha12>/<path> → COPY INTO → 14,060 rows + ledger
make sf-bronze                                # again: "nothing new to ingest" (ledger + Snowflake load history both say so)
make sf-verify                                # plain-Python row counts per landed file vs. bronze
make sf-silver-gold                           # dbt seed; dbt build = silver, gold, 70+ tests
make sf-parity                                # vs. space/data/gold.json → docs/parity_report.md
make sf-all                                   # the four in a row
```

`make sf-bronze SF_BRONZE_FLAGS=--force` re-appends (and passes FORCE=TRUE to COPY, or Snowflake's load history would
refuse the same stage object). `make sf-show SF_SHOW_STAGE=1` lists bronze and the stage.

## What is where

| | Spark | Snowflake |
|---|---|---|
| landing | `data/landing/` (committed) | the same files, PUT to `@LANDING/<sha256[:12]>/<landed_relpath>` |
| bronze idempotency | (path, sha256) in the table ∪ ledger | the same check in Python, *and* COPY INTO's own load history keyed by the stage object (which has the sha in its path) |
| bronze row-count check | `make verify` (Python counts vs Delta) | `make sf-verify` (Python counts vs Snowflake) + the same check at COPY time + the dbt test `assert_bronze_row_counts_match_landing` |
| JSON → records | Python reader builds the rows | COPY loads the document whole into `bronze_raw_json` (VARIANT); `INSERT … SELECT … LATERAL FLATTEN` carves out series/runs/sweep tables (COPY transformations cannot FLATTEN) |
| snapshot selection | silver joins bronze to the manifest's (path, sha) pairs | `LANDING.MANIFEST_SNAPSHOT` table + `current_snapshot()` macro; `assert_snapshot_in_bronze` refuses an incomplete bronze |
| silver / gold | PySpark DataFrame code, overwrite each run | dbt models (`table` materialisation = rebuilt each run) |
| invariants | 28 pytest tests (9 run Spark) | 72 dbt tests: generic (not_null / unique / accepted_values / relationships) + 12 singular SQL tests, one per pytest invariant that is about the data |
| medians | `percentile_approx` (observed value at rank ⌈q·n⌉) | `PERCENTILE_DISC` (the same element) |
| timestamps | UTC session, `date_format … 'Z'` before collect | `TIMESTAMP_NTZ` holding UTC; `CONVERT_TIMEZONE` at parse time |
