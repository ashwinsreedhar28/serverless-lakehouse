"""Run snowflake/setup.sql statement by statement as ACCOUNTADMIN, then grant LAKEHOUSE_ROLE to SNOWFLAKE_USER.

    python -m lakehouse.sf.setup

Needs the key pair registered on the user first (see snowflake/README.md). Idempotent: every statement is
CREATE … IF NOT EXISTS / CREATE OR REPLACE FILE FORMAT / GRANT.
"""

from __future__ import annotations

import sys

from ..config import REPO_ROOT
from .client import connect, load_env, run

SETUP_SQL = REPO_ROOT / "snowflake" / "setup.sql"


def statements(text: str) -> list[str]:
    out, buf = [], []
    for line in text.splitlines():
        stripped = line.split("--", 1)[0].rstrip()
        if not stripped.strip():
            continue
        buf.append(stripped)
        if stripped.endswith(";"):
            out.append("\n".join(buf)[:-1])
            buf = []
    return out


def main(argv: list[str] | None = None) -> int:
    cfg = load_env()
    conn = connect("LANDING", role="ACCOUNTADMIN")
    cur = conn.cursor()
    try:
        for s in statements(SETUP_SQL.read_text(encoding="utf-8")):
            head = " ".join(s.split())[:90]
            run(cur, s)
            print(f"  ok  {head}")
        run(cur, f"GRANT ROLE LAKEHOUSE_ROLE TO USER {cfg['SNOWFLAKE_USER']}")
        print(f"  ok  GRANT ROLE LAKEHOUSE_ROLE TO USER {cfg['SNOWFLAKE_USER']}")
        wh = run(cur, "SHOW WAREHOUSES LIKE 'LAKEHOUSE_WH'")
        print(f"setup: done — warehouse {wh[0][0]} size={wh[0][3]} auto_suspend={wh[0][11]}s; try `make sf-bronze`")
        return 0
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
