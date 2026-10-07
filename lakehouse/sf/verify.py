"""Bronze completeness check on Snowflake: for every landed file, the target table must hold exactly the number of
rows the file contains — counted here with plain Python (json / csv / splitlines), not by Snowflake, so the check is
not grading itself. Same contract and output as lakehouse.verify.

    python -m lakehouse.sf.verify

Exit 0 when every (file, table) pair matches; 1 otherwise. A 2× count means the file was appended twice (--force).
Also prints what Snowflake's own load history says (COPY_HISTORY, last 14 days) next to the ledger, so the two
bookkeeping systems can be compared: load history counts stage objects; the ledger counts (table, file, sha) appends.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..config import LANDING_DIR, MANIFEST_PATH
from .client import connect, run
from .counts import expected_rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--landing-dir", type=Path, default=LANDING_DIR)
    args = ap.parse_args(argv)
    manifest = json.loads((args.landing_dir / MANIFEST_PATH.name).read_text(encoding="utf-8"))

    conn = connect("BRONZE")
    cur = conn.cursor()
    try:
        tables = sorted({t for e in manifest["files"] for t in expected_rows(args.landing_dir / e["landed_relpath"], e["dataset"])})
        existing = {r[0].lower() for r in run(cur, "SELECT table_name FROM LAKEHOUSE.information_schema.tables WHERE table_schema = 'BRONZE'")}
        actual: dict[tuple[str, str, str], int] = {}
        for t in tables:
            if t not in existing:
                continue
            for f, sha, n in run(cur, f"SELECT source_file, source_sha256, COUNT(*) FROM BRONZE.{t} GROUP BY 1, 2"):
                actual[(t, f, sha)] = n

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
        print(f"verify: {len(manifest['files'])} files, {total_expected:,} expected rows, {total_actual:,} found, "
              f"{bad} mismatching file→table pairs → {'OK' if bad == 0 else 'FAIL'}")

        # Snowflake's bookkeeping beside ours. COPY_HISTORY is per table and per stage object (the sha-prefixed path);
        # the ledger is per (table, file, sha) including the FLATTEN inserts, which no COPY ever saw.
        n_copy = 0
        for t in tables:
            if t not in existing:
                continue
            rows = run(cur, f"SELECT COUNT(*), SUM(row_count), SUM(IFF(status = 'Loaded', 0, 1)) "
                            f"FROM TABLE(LAKEHOUSE.information_schema.copy_history(TABLE_NAME => 'BRONZE.{t.upper()}', "
                            f"START_TIME => DATEADD(day, -14, CURRENT_TIMESTAMP())))")
            n_copy += rows[0][0] or 0
        ledger = run(cur, "SELECT COUNT(*), SUM(rows), SUM(IFF(reconciled, 1, 0)), SUM(IFF(loader = 'copy_into', 1, 0)) FROM BRONZE.bronze_ingest_log")[0]
        print(f"  load history (COPY_HISTORY, 14 d): {n_copy} file loads   ledger: {ledger[0]} appends, {ledger[1]:,} rows, "
              f"{ledger[3]} by COPY INTO, {ledger[2]} reconciled")
        return 0 if bad == 0 else 1
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
