"""Runpod API snapshots → @RUNPOD → BRONZE.bronze_runpod_polls, by COPY INTO with Snowflake's own load history as the only
"already loaded" check — the contrast case to lakehouse.sf.bronze, which keeps its own ledger beside it.

    python -m lakehouse.sf.runpod load [--run-label …]      COPY every not-yet-loaded snapshot in @RUNPOD, log the result
    python -m lakehouse.sf.runpod put <file> <sha256>      (what tools/runpod_poll.py calls after writing a snapshot)

The stage path carries the document's full sha256 (@RUNPOD/<sha256>/polls/<name>.json.gz), so COPY INTO's per-object
load history is keyed by content, not just by name, and the lineage columns can be filled from METADATA$FILENAME alone.
A PATTERN COPY with FORCE=FALSE loads whatever is new and skips the rest; the COPY result rows become ledger rows.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from .bronze import LINEAGE_DDL, lit, ts_lit
from .client import connect, run

STAGE = "@LAKEHOUSE.LANDING.RUNPOD"
TABLE = "bronze_runpod_polls"


def ensure_table(cur) -> None:
    run(cur, f"CREATE TABLE IF NOT EXISTS BRONZE.{TABLE} (doc VARIANT NOT NULL, {LINEAGE_DDL})")


def put_snapshot(path: Path, sha: str) -> str:
    conn = connect("BRONZE")
    cur = conn.cursor()
    try:
        rows = run(cur, f"PUT 'file://{path.resolve().as_posix()}' '{STAGE}/{sha}/polls/' AUTO_COMPRESS=TRUE OVERWRITE=FALSE")
        return rows[0][6] if rows else "?"
    finally:
        cur.close()
        conn.close()


def load(run_label: str) -> int:
    ingested_at = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
    conn = connect("BRONZE")
    cur = conn.cursor()
    try:
        ensure_table(cur)
        rows = run(cur, f"""
            COPY INTO BRONZE.{TABLE} (doc, stage_path, ingested_at, run_label, source_file, source_sha256)
            FROM (SELECT $1, METADATA$FILENAME, {ts_lit(ingested_at)}, {lit(run_label)},
                         'runpod/polls/' || REGEXP_REPLACE(REGEXP_SUBSTR(METADATA$FILENAME, '[^/]+$'), '\\\\.gz$', ''),
                         REGEXP_SUBSTR(METADATA$FILENAME, '[0-9a-f]{{64}}')
                  FROM {STAGE}/)
            PATTERN = '.*polls/.*\\\\.json(\\\\.gz)?'
            FILE_FORMAT = (FORMAT_NAME = 'LAKEHOUSE.LANDING.FF_JSON_DOC')
            ON_ERROR = ABORT_STATEMENT FORCE = FALSE""")
        loaded = [r for r in rows if r[1] == "LOADED"]
        if rows and rows[0][0] == "Copy executed with 0 files processed.":
            loaded = []
        for r in loaded:
            name = r[0].rsplit("/", 1)[-1].removesuffix(".gz")
            sha = next((seg for seg in r[0].split("/") if len(seg) == 64), "")
            cur.execute("INSERT INTO BRONZE.bronze_ingest_log VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (run_label, TABLE, f"runpod/polls/{name}", sha, r[3], ingested_at, False, "copy_into", r[1]))
        n_polls, latest = run(cur, f"SELECT COUNT(*), TO_CHAR(MAX(doc:polled_at::timestamp_tz), 'YYYY-MM-DD HH24:MI') FROM BRONZE.{TABLE}")[0]
        print(f"runpod load: {len(loaded)} new snapshot(s) loaded, {len(rows) - len(loaded) if rows else 0} skipped by load history; "
              f"{n_polls} polls in bronze, latest {latest}")
        return 0
    finally:
        cur.close()
        conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_load = sub.add_parser("load")
    p_load.add_argument("--run-label", default=datetime.now(timezone.utc).strftime("runpod_%Y-%m-%dT%H%MZ"))
    p_put = sub.add_parser("put")
    p_put.add_argument("file", type=Path)
    p_put.add_argument("sha256")
    args = ap.parse_args(argv)
    if args.cmd == "load":
        return load(args.run_label)
    print(put_snapshot(args.file, args.sha256))
    return 0


if __name__ == "__main__":
    sys.exit(main())
