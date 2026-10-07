"""Print what is in Snowflake bronze: rows, files, run_labels, latest ingest per table, and the stage listing.

    python -m lakehouse.sf.show [--stage]
"""

from __future__ import annotations

import argparse
import sys

from .bronze import BRONZE_TABLES
from .client import connect, run


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", action="store_true", help="also LIST @LANDING")
    args = ap.parse_args(argv)
    conn = connect("BRONZE")
    cur = conn.cursor()
    try:
        existing = {r[0].lower() for r in run(cur, "SELECT table_name FROM LAKEHOUSE.information_schema.tables WHERE table_schema = 'BRONZE'")}
        print(f"{'table':<34} {'rows':>8} {'files':>6} {'run_labels':>10}  latest_ingested_at (UTC)")
        for t in BRONZE_TABLES:
            if t not in existing:
                print(f"{t:<34} {'-':>8}")
                continue
            r = run(cur, f"SELECT COUNT(*), COUNT(DISTINCT source_file || source_sha256), COUNT(DISTINCT run_label), "
                         f"TO_CHAR(MAX(ingested_at), 'YYYY-MM-DD HH24:MI:SS') FROM BRONZE.{t}")[0]
            print(f"{t:<34} {r[0]:>8,} {r[1]:>6} {r[2]:>10}  {r[3]}")
        try:
            cr = run(cur, "SELECT ROUND(SUM(credits_used), 3), MIN(start_time)::date FROM TABLE(LAKEHOUSE.information_schema.warehouse_metering_history("
                          "DATEADD(day, -30, CURRENT_TIMESTAMP()), CURRENT_TIMESTAMP(), 'LAKEHOUSE_WH'))")[0]
            print(f"\ncredits used by LAKEHOUSE_WH since {cr[1]}: {cr[0]} (trial grants $400 ≈ 100–130 credits depending on edition)")
        except Exception as e:      # MONITOR on the warehouse not granted yet (re-run `make sf-setup`)
            print(f"\ncredits used: not readable ({str(e).splitlines()[0][:80]})")
        if args.stage:
            print("\n@LANDING:")
            for row in run(cur, "LIST @LAKEHOUSE.LANDING.LANDING"):
                print(f"  {row[1]:>9}  {row[0]}")
        return 0
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
