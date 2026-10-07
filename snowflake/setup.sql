-- serverless-lakehouse on Snowflake: one-time account setup. Run once as ACCOUNTADMIN in a worksheet
-- (or `make sf-setup`, which runs it through the Python connector with the credentials in snowflake/.env).
--
-- Everything the pipeline touches lives in one database with one schema per layer:
--   LAKEHOUSE.LANDING   internal stage @LANDING (the landed files, byte for byte, under <sha256[:12]>/<path>),
--                       the landing manifest as a table, and the parity stage @PARITY
--   LAKEHOUSE.BRONZE    COPY INTO targets: raw, append-only, lineage columns, plus the ingest ledger
--   LAKEHOUSE.SILVER    dbt models + dbt seeds (the seeds/ CSVs)
--   LAKEHOUSE.GOLD      dbt models the parity check compares with the Spark gold tables
--
-- Credits: the trial grants $400 for 30 days. Only a running warehouse spends them, so the warehouse is X-Small,
-- suspends after 60 s idle, and a resource monitor cuts it off at 20 credits (~$40–60 depending on edition) in
-- case something loops. The whole build (47 files, ~14k bronze rows, a few dozen dbt runs) is a few credits.

USE ROLE ACCOUNTADMIN;

CREATE WAREHOUSE IF NOT EXISTS LAKEHOUSE_WH
  WAREHOUSE_SIZE = XSMALL
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE
  COMMENT = 'serverless-lakehouse: bronze COPY INTO + dbt silver/gold';

CREATE RESOURCE MONITOR IF NOT EXISTS LAKEHOUSE_MONITOR
  WITH CREDIT_QUOTA = 20
  FREQUENCY = NEVER
  START_TIMESTAMP = IMMEDIATELY
  TRIGGERS ON 75 PERCENT DO NOTIFY
           ON 100 PERCENT DO SUSPEND_IMMEDIATE;
ALTER WAREHOUSE LAKEHOUSE_WH SET RESOURCE_MONITOR = LAKEHOUSE_MONITOR;

CREATE DATABASE IF NOT EXISTS LAKEHOUSE;
CREATE SCHEMA IF NOT EXISTS LAKEHOUSE.LANDING;
CREATE SCHEMA IF NOT EXISTS LAKEHOUSE.BRONZE;
CREATE SCHEMA IF NOT EXISTS LAKEHOUSE.SILVER;
CREATE SCHEMA IF NOT EXISTS LAKEHOUSE.GOLD;

-- Internal named stages. Files are PUT here gzip-compressed (the connector's default); COPY INTO inflates them.
-- @LANDING mirrors data/landing/ one level down: <sha256 prefix>/<landed_relpath>, so a changed file (new sha)
-- is a new object and Snowflake's own load history (keyed by stage path) agrees with the ledger's (path, sha) key.
CREATE STAGE IF NOT EXISTS LAKEHOUSE.LANDING.LANDING
  DIRECTORY = (ENABLE = TRUE)
  COMMENT = 'data/landing/ mirror, keyed by sha256 prefix';
CREATE STAGE IF NOT EXISTS LAKEHOUSE.LANDING.PARITY
  COMMENT = 'Spark gold export (space/data/gold.json) for the parity check';
CREATE STAGE IF NOT EXISTS LAKEHOUSE.LANDING.RUNPOD
  DIRECTORY = (ENABLE = TRUE)
  COMMENT = 'Runpod API snapshots written by tools/runpod_poll.py (GitHub Actions cron)';

-- File formats. Every option that would make Snowflake *interpret* bytes is turned off: bronze keeps the file's
-- characters as they are, like the Spark readers do.
--   worker logs: one line = one row. No field delimiter, no enclosure, no escape (the vLLM lines carry literal
--   backslashes), empty line = empty string not NULL, and SKIP_BLANK_LINES=FALSE so a blank line fails loudly instead
--   of silently dropping a row the Python line count expects.
CREATE OR REPLACE FILE FORMAT LAKEHOUSE.LANDING.FF_LOG_LINES
  TYPE = CSV
  FIELD_DELIMITER = NONE
  RECORD_DELIMITER = '\n'
  FIELD_OPTIONALLY_ENCLOSED_BY = NONE
  ESCAPE = NONE
  ESCAPE_UNENCLOSED_FIELD = NONE
  EMPTY_FIELD_AS_NULL = FALSE
  NULL_IF = ()
  SKIP_BLANK_LINES = FALSE
  TRIM_SPACE = FALSE
  ENCODING = 'UTF8';

--   Pulse CSVs: quoted fields hold JSON with doubled quotes and embedded newlines. Empty unquoted field = NULL (Spark's
--   default too), no escape character, no NULL_IF so a literal \N stays text, column-count mismatch is an error.
CREATE OR REPLACE FILE FORMAT LAKEHOUSE.LANDING.FF_PULSE_CSV
  TYPE = CSV
  SKIP_HEADER = 1
  FIELD_DELIMITER = ','
  RECORD_DELIMITER = '\n'
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  ESCAPE = NONE
  ESCAPE_UNENCLOSED_FIELD = NONE
  EMPTY_FIELD_AS_NULL = TRUE
  NULL_IF = ()
  ERROR_ON_COLUMN_COUNT_MISMATCH = TRUE
  TRIM_SPACE = FALSE
  ENCODING = 'UTF8';

--   emberserve JSON: one document per file (top-level object), kept whole as a VARIANT. The record-grained bronze tables
--   are carved out of it with FLATTEN afterwards — COPY INTO transformations cannot FLATTEN.
CREATE OR REPLACE FILE FORMAT LAKEHOUSE.LANDING.FF_JSON_DOC
  TYPE = JSON
  STRIP_OUTER_ARRAY = FALSE
  STRIP_NULL_VALUES = FALSE
  IGNORE_UTF8_ERRORS = FALSE;

-- A role for the pipeline (dbt and the Python loader connect as it). Grant it to your user in the trial.
CREATE ROLE IF NOT EXISTS LAKEHOUSE_ROLE;
GRANT USAGE, OPERATE ON WAREHOUSE LAKEHOUSE_WH TO ROLE LAKEHOUSE_ROLE;
GRANT USAGE ON DATABASE LAKEHOUSE TO ROLE LAKEHOUSE_ROLE;
GRANT ALL ON ALL SCHEMAS IN DATABASE LAKEHOUSE TO ROLE LAKEHOUSE_ROLE;
GRANT ALL ON FUTURE TABLES IN DATABASE LAKEHOUSE TO ROLE LAKEHOUSE_ROLE;
GRANT ALL ON FUTURE VIEWS IN DATABASE LAKEHOUSE TO ROLE LAKEHOUSE_ROLE;
GRANT ALL ON ALL STAGES IN SCHEMA LAKEHOUSE.LANDING TO ROLE LAKEHOUSE_ROLE;
GRANT USAGE ON ALL FILE FORMATS IN SCHEMA LAKEHOUSE.LANDING TO ROLE LAKEHOUSE_ROLE;
GRANT ROLE LAKEHOUSE_ROLE TO ROLE SYSADMIN;
-- GRANT ROLE LAKEHOUSE_ROLE TO USER <your_user>;   -- `make sf-setup` fills this in from SNOWFLAKE_USER
