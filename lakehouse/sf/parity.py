"""Parity: the Snowflake gold tables vs. the Spark gold export, table by table, row by row.

    python -m lakehouse.sf.parity [--spark-json space/data/gold.json] [--out docs/parity_report.md]

The Spark side is space/data/gold.json, which `make dashboard` writes from the Delta gold tables (every value already
normalised: timestamps as UTC 'Z' strings at second precision, NaN → null, inf → "inf", gold_built_at dropped). The
Snowflake side is read live and pushed through the same normalisation. For each of the eight tables the report gives
the row counts, the number of rows that match exactly (floats within 1e-6 relative), and every unmatched row from
either side with the column(s) that differ from its nearest counterpart. Exit 0 only when all eight tables match.

Rows are matched on the table's natural key (its group-by columns), so a float that drifts shows up as "that row,
that column", not as two whole unmatched rows.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from ..config import GOLD_TABLES, REPO_ROOT
from .client import connect, run

# natural keys: what one row of each gold table *is* (the Spark groupBy / select keys)
KEYS = {
    "gold_coldstart_by_gpu_image": ["engine", "model", "gpu_model", "gpu_tier", "weights_mode", "flashboot", "kind"],
    "gold_flashboot_hit_rate": ["engine", "model", "endpoint_id", "flashboot_setting"],
    "gold_engine_comparison": ["engine", "weights_mode", "scope", "cohort"],
    "gold_worker_boot_phases": ["source_file", "boot_index"],
    "gold_cost_per_job": ["engine", "model", "gpu_model", "gpu_tier", "weights_mode", "kind", "price_per_hr_usd"],
    "gold_scoring_cost_per_batch": ["batch_id"],
    "gold_sweep_latency": ["source_file", "system", "request_rate"],
    "gold_coldstart_events": ["source_file", "series_label", "endpoint_id", "run_index", "request_ts_utc", "delay_ms"],
}
REL_TOL = 1e-6
ABS_TOL = 1e-9


def norm(v):
    """Same shape lakehouse.dashboard.jsonable gives the Spark side."""
    if isinstance(v, float):
        if math.isnan(v):
            return None
        if math.isinf(v):
            return "inf"
        return v
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("[") and s.endswith("]"):       # ARRAY columns come back as JSON text
            try:
                return [norm(x) for x in json.loads(s)]
            except ValueError:
                return v
        return v
    if isinstance(v, (list, tuple)):
        return [norm(x) for x in v]
    return v


def same(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=REL_TOL, abs_tol=ABS_TOL)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def keyof(row: dict, keys: list[str]) -> tuple:
    return tuple(json.dumps(norm(row.get(k)), sort_keys=True) for k in keys)


def compare(name: str, spark: list[dict], snow: list[dict]) -> tuple[bool, list[str]]:
    keys = KEYS[name]
    cols = sorted(set().union(*[r.keys() for r in spark + snow]) - {"gold_built_at"})
    only_spark = sorted(set(spark[0]) - set(snow[0]) - {"gold_built_at"}) if spark and snow else []
    only_snow = sorted(set(snow[0]) - set(spark[0]) - {"gold_built_at"}) if spark and snow else []
    lines = [f"### {name}", "", f"- rows: Spark {len(spark)}, Snowflake {len(snow)}"]
    if only_spark or only_snow:
        lines.append(f"- columns only in Spark: {only_spark or '—'}; only in Snowflake: {only_snow or '—'}")
    s_idx = {}
    for r in spark:
        s_idx.setdefault(keyof(r, keys), []).append(r)
    n_idx = {}
    for r in snow:
        n_idx.setdefault(keyof(r, keys), []).append(r)
    matched = 0
    diffs: list[str] = []
    for k in sorted(set(s_idx) | set(n_idx)):
        a, b = s_idx.get(k, []), n_idx.get(k, [])
        if len(a) != len(b):
            diffs.append(f"- key {dict(zip(keys, (json.loads(x) for x in k)))}: {len(a)} Spark row(s) vs {len(b)} Snowflake row(s)")
            continue
        # same cardinality: pair them in column-sorted order
        a = sorted(a, key=lambda r: json.dumps(norm([r.get(c) for c in cols]), sort_keys=True, default=str))
        b = sorted(b, key=lambda r: json.dumps(norm([r.get(c) for c in cols]), sort_keys=True, default=str))
        for ra, rb in zip(a, b):
            bad = [c for c in cols if not same(norm(ra.get(c)), norm(rb.get(c)))]
            if bad:
                detail = "; ".join(f"{c}: spark={norm(ra.get(c))!r} snowflake={norm(rb.get(c))!r}" for c in bad)
                diffs.append(f"- key {dict(zip(keys, (json.loads(x) for x in k)))}: {detail}")
            else:
                matched += 1
    ok = not diffs and len(spark) == len(snow) and matched == len(spark)
    lines.append(f"- rows matched: {matched} of {max(len(spark), len(snow))} → **{'MATCH' if ok else 'DIFF'}**")
    lines += diffs
    lines.append("")
    return ok, lines


def read_snowflake(cur, name: str) -> list[dict]:
    cur.execute(f"SELECT * FROM GOLD.{name}")
    cols = [d[0].lower() for d in cur.description]
    return [dict(zip(cols, (norm(v) for v in row))) for row in cur.fetchall()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spark-json", type=Path, default=REPO_ROOT / "space" / "data" / "gold.json")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "docs" / "parity_report.md")
    args = ap.parse_args(argv)
    payload = json.loads(args.spark_json.read_text(encoding="utf-8"))

    conn = connect("GOLD")
    cur = conn.cursor()
    try:
        results = []
        report = [f"# Parity: Snowflake gold vs Spark gold", "",
                  f"Spark side: `{args.spark_json.relative_to(REPO_ROOT)}` (built {payload['meta']['built_at_utc']}). "
                  f"Snowflake side: `LAKEHOUSE.GOLD` read {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}. "
                  f"Floats compared within {REL_TOL:g} relative; timestamps at second precision; NaN ≡ null; arrays element-wise.", ""]
        for name in GOLD_TABLES:
            spark_rows = [{k: norm(v) for k, v in r.items()} for r in payload[name]]
            snow_rows = read_snowflake(cur, name)
            ok, lines = compare(name, spark_rows, snow_rows)
            results.append((name, ok, len(spark_rows), len(snow_rows)))
            report += lines
            print(f"  {name:<30} spark={len(spark_rows):>3} snowflake={len(snow_rows):>3}  {'MATCH' if ok else 'DIFF'}")
        n_ok = sum(1 for _, ok, _, _ in results if ok)
        summary = [f"**{n_ok} of {len(results)} tables match.**", "", "| table | Spark rows | Snowflake rows | result |", "|---|---|---|---|"]
        summary += [f"| {n} | {a} | {b} | {'MATCH' if ok else 'DIFF'} |" for n, ok, a, b in results]
        report = report[:4] + summary + [""] + report[4:]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(report) + "\n", encoding="utf-8")
        print(f"parity: {n_ok}/{len(results)} tables match → {args.out.relative_to(REPO_ROOT)}")
        return 0 if n_ok == len(results) else 1
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
