"""Export the gold layer for the two dashboards.

    python -m lakehouse.dashboard [--format delta|parquet] [--out docs/dashboard.html] [--json-out space/data/gold.json]

Writes the same gold snapshot twice: embedded in docs/dashboard.html (a static page, SVG charts drawn in the
browser, opens from disk or GitHub Pages) and as space/data/gold.json, which the Streamlit app in space/ reads
on Hugging Face. Neither dashboard computes a metric itself — they draw what gold already says, so "what the
dashboard shows" and "what the tables say" are the same thing. Rebuild with `make gold && make dashboard`.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from .config import FLASHBOOT_HIT_MS, GOLD_TABLES, REPO_ROOT, table_path
from .spark import get_spark, timestamps_as_utc_strings

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
    ap.add_argument("--json-out", type=Path, default=REPO_ROOT / "space" / "data" / "gold.json")
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
        df = timestamps_as_utc_strings(df.select(*cols))      # UTC strings before collect(); never driver-local datetimes
        payload[name] = [{c: jsonable(r[c]) for c in cols} for r in df.collect()]
    spark.stop()

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
    print(f"dashboard: {len(GOLD_TABLES)} gold tables, {rows} rows → {shown(args.out)} "
          f"({args.out.stat().st_size / 1024:.0f} KB) and {shown(args.json_out)} "
          f"({args.json_out.stat().st_size / 1024:.0f} KB)")
    return 0


def shown(p: Path) -> str:
    """Repo-relative when inside the repo, absolute otherwise (an --out under /tmp must not crash after writing)."""
    try:
        return str(p.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


if __name__ == "__main__":
    sys.exit(main())
