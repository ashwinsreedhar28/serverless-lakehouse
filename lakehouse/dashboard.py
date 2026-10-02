"""Render the gold layer as a self-contained dashboard page: docs/dashboard.html.

    python -m lakehouse.dashboard [--format delta|parquet] [--out docs/dashboard.html]

The page is static: every gold table is embedded as JSON and the charts are drawn in the browser, so the
file opens from disk, from GitHub Pages, or as a shared artifact with no server behind it. Rebuilding the
dashboard is `make gold && make dashboard`; the page never computes a metric itself — it only draws what
gold already says, which keeps "what the dashboard shows" and "what the tables say" the same thing.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from .config import FLASHBOOT_HIT_MS, GOLD_TABLES, REPO_ROOT, table_path
from .spark import get_spark

TEMPLATE = Path(__file__).with_name("templates") / "dashboard.html"


def jsonable(v):
    if isinstance(v, float):
        if math.isnan(v):
            return None
        if math.isinf(v):
            return "inf"
        return v
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v]
    return v


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--format", default="delta", choices=["delta", "parquet"])
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "docs" / "dashboard.html")
    args = ap.parse_args(argv)
    spark = get_spark(args.format, app="gold-dashboard")

    payload: dict = {"meta": {
        "built_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "flashboot_hit_ms": FLASHBOOT_HIT_MS,
        "repo": "github.com/ashwinsreedhar28/serverless-lakehouse",
    }}
    for name in GOLD_TABLES:
        df = spark.read.format(args.format).load(str(table_path(name)))
        cols = [c for c in df.columns if c != "gold_built_at"]
        payload[name] = [{c: jsonable(r[c]) for c in cols} for r in df.select(*cols).collect()]
    spark.stop()

    html = TEMPLATE.read_text(encoding="utf-8")
    marker = "/*GOLD_JSON*/null"
    if marker not in html:
        print("dashboard: template is missing the GOLD_JSON marker", file=sys.stderr)
        return 2
    html = html.replace(marker, json.dumps(payload, separators=(",", ":")).replace("</", "<\\/"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    rows = sum(len(v) for k, v in payload.items() if k != "meta")
    print(f"dashboard: {len(GOLD_TABLES)} gold tables, {rows} rows embedded → {args.out.relative_to(REPO_ROOT)} "
          f"({args.out.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
