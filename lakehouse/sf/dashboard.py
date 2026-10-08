"""Export the Snowflake GOLD schema for the static dashboard — the same page `make dashboard` renders from Spark gold,
built from the other backend, plus the tables only dbt has (the measurement campaign and the Runpod live source).

    python -m lakehouse.sf.dashboard [--out docs/dashboard.html] [--json-out space/data/gold_snowflake.json]

Every GOLD table is exported under its lowercase name, so the eight parity tables land under the keys the template
already reads, and the campaign / runpod tables under theirs; the template draws those sections only when the keys are
present. `meta.backend` says which backend built the page. The Spark export (space/data/gold.json) is left alone —
`make sf-parity` reads it as the Spark side of the comparison.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from ..config import FLASHBOOT_HIT_MS, REPO_ROOT
from .client import connect, run

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "dashboard.html"   # shared with lakehouse.dashboard (Spark)


def shown(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def jsonable(v):
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    if isinstance(v, float):
        if math.isnan(v):
            return None
        if math.isinf(v):
            return "inf"
        return v
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%dT%H:%M:%SZ")      # TIMESTAMP_NTZ in this warehouse is always UTC (dbt macro to_utc)
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, str) and v[:1] in "[{":       # ARRAY / OBJECT columns come back as JSON text
        try:
            return json.loads(v)
        except ValueError:
            return v
    return v


def planned_cold_starts() -> int | None:
    """Sum of n_cold over campaign/estimate.csv (the approved plan), for the KPI's denominator."""
    import csv
    p = REPO_ROOT / "campaign" / "estimate.csv"
    if not p.is_file():
        return None
    with p.open(newline="", encoding="utf-8") as f:
        return sum(int(r.get("n_cold") or 0) for r in csv.DictReader(f))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "docs" / "dashboard.html")
    ap.add_argument("--json-out", type=Path, default=REPO_ROOT / "space" / "data" / "gold_snowflake.json")
    args = ap.parse_args(argv)

    conn = connect("GOLD")
    cur = conn.cursor()
    try:
        names = [r[0].lower() for r in run(cur, "SELECT table_name FROM LAKEHOUSE.information_schema.tables "
                                                "WHERE table_schema = 'GOLD' AND table_type = 'BASE TABLE' ORDER BY 1")]
        payload: dict = {"meta": {
            "built_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "flashboot_hit_ms": FLASHBOOT_HIT_MS,
            "repo": "github.com/ashwinsreedhar28/serverless-lakehouse",
            "backend": "snowflake",
            "source": "LAKEHOUSE.GOLD (dbt models over the Snowflake bronze layer)",
            "campaign_planned_cold_starts": planned_cold_starts(),
        }}
        for name in names:
            rows = run(cur, f"SELECT * FROM GOLD.{name}")
            cols = [d[0].lower() for d in cur.description]
            keep = [i for i, c in enumerate(cols) if c != "gold_built_at"]
            payload[name] = [{cols[i]: jsonable(r[i]) for i in keep} for r in rows]
    finally:
        cur.close()
        conn.close()

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=0), encoding="utf-8")
    html = TEMPLATE.read_text(encoding="utf-8")
    marker = "/*GOLD_JSON*/null"
    if marker not in html:
        print("dashboard: template is missing the GOLD_JSON marker", file=sys.stderr)
        return 2
    html = html.replace(marker, json.dumps(payload, separators=(",", ":")).replace("</", "<\\/"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    rows = sum(len(v) for k, v in payload.items() if k != "meta")
    print(f"dashboard(snowflake): {len(names)} gold tables, {rows} rows → {shown(args.out)} "
          f"({args.out.stat().st_size / 1024:.0f} KB) and {shown(args.json_out)} ({args.json_out.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
