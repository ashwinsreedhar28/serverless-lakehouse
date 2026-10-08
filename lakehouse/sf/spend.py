"""Spend log: what the Runpod account actually billed per endpoint per day (from the poller's hourly billing records,
Runpod's own numbers) beside what the campaign and load generator estimated, with the 20 % rule applied.

    python -m lakehouse.sf.spend [--out docs/spend_log.md] [--check]

Inputs
- SILVER.silver_runpod_billing_hourly — $ per endpoint per hour, as GET /v2/billing/serverless reported it (latest poll wins)
- campaign/runs.csv — one row per campaign slot that ran: date_utc, cell, endpoint_id, n_cold, est_usd, note (written by tools/campaign.py)
- campaign/estimate.csv — the per-cell estimate the campaign was approved on (cell, endpoint_id when created, est_usd_total)
- the load generator's estimate: LOADGEN_EST_USD_PER_RUN × runs seen in landing (data/landing/runpod/loadgen/*.json)

Exit 1 with --check when any endpoint's actual spend exceeds its estimate by more than 20 % (the campaign driver and the
runpod-load workflow both call it that way, so an overrun stops the next slot and shows up as a red run).
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from ..config import LANDING_DIR, REPO_ROOT
from .client import connect, run

CAMPAIGN_DIR = REPO_ROOT / "campaign"
LOADGEN_EST_USD_PER_RUN = 0.013       # 17 s boot + 15 s requests + 10 s idle on a $1.10/hr RTX 4090 PRO; see the README estimate
OVERRUN = 0.20


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "docs" / "spend_log.md")
    ap.add_argument("--check", action="store_true", help="exit 1 on a >20 %% overrun")
    args = ap.parse_args(argv)

    conn = connect("SILVER")
    cur = conn.cursor()
    try:
        names = {r[0]: r[1] for r in run(cur, "SELECT endpoint_id, name FROM SILVER.silver_runpod_endpoints "
                                              "QUALIFY ROW_NUMBER() OVER (PARTITION BY endpoint_id ORDER BY poll_seq DESC) = 1")}
        daily = run(cur, "SELECT endpoint_id, bucket_start_utc::date, ROUND(SUM(total_usd), 4), ROUND(SUM(gpu_usd), 4), COUNT(*) "
                         "FROM SILVER.silver_runpod_billing_hourly GROUP BY 1, 2 ORDER BY 2, 1")
        first_poll, last_poll = run(cur, "SELECT MIN(polled_at_utc), MAX(polled_at_utc) FROM SILVER.silver_runpod_polls")[0]
    finally:
        cur.close()
        conn.close()

    actual_by_ep: dict[str, float] = defaultdict(float)
    for ep, day, total, gpu, n in daily:
        actual_by_ep[ep] += float(total or 0)

    # campaign/spend_ack.csv: overruns the owner has reviewed (date_utc, endpoint_id, usd, reason). They stay in the actuals
    # and in this log; they come off the 20 % check so a known, fixed incident does not block every later slot.
    acks = read_csv(CAMPAIGN_DIR / "spend_ack.csv")
    ack_by_ep: dict[str, float] = defaultdict(float)
    for r in acks:
        if r.get("endpoint_id"):
            ack_by_ep[r["endpoint_id"]] += float(r.get("usd") or 0)
    runs = read_csv(CAMPAIGN_DIR / "runs.csv")
    estimates = read_csv(CAMPAIGN_DIR / "estimate.csv")
    est_by_ep: dict[str, float] = defaultdict(float)
    for r in runs:
        if r.get("endpoint_id"):
            est_by_ep[r["endpoint_id"]] += float(r.get("est_usd") or 0)
    loadgen_runs = sorted((LANDING_DIR / "runpod" / "loadgen").glob("*.json")) if (LANDING_DIR / "runpod" / "loadgen").is_dir() else []
    loadgen_ep = {r["endpoint_id"] for r in runs if r.get("cell") == "loadgen"}
    for ep in loadgen_ep:
        est_by_ep[ep] += LOADGEN_EST_USD_PER_RUN * len(loadgen_runs)

    lines = ["# Spend log", "",
             f"Actual $ from Runpod's `GET /v2/billing/serverless` (hourly buckets, via the poller; polls {first_poll} → {last_poll} UTC). "
             f"Estimates from `campaign/runs.csv` and {LOADGEN_EST_USD_PER_RUN:.3f} $/run for the load generator. "
             f"Rule: stop when an endpoint's actual exceeds its estimate by {OVERRUN:.0%}. Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.",
             "", "## Per endpoint", "", "| endpoint | name | estimated $ | actual $ | acknowledged $ | ratio (actual − ack) / est | status |", "|---|---|---|---|---|---|---|"]
    overruns = []
    for ep in sorted(set(actual_by_ep) | set(est_by_ep)):
        est, act, ack = est_by_ep.get(ep, 0.0), actual_by_ep.get(ep, 0.0), ack_by_ep.get(ep, 0.0)
        ratio = ((act - ack) / est) if est else None
        status = "—"
        if est:
            status = "OVER 20 %" if (act - ack) > est * (1 + OVERRUN) else "ok"
            if status.startswith("OVER"):
                overruns.append((ep, est, act - ack))
        lines.append(f"| {ep} | {names.get(ep, '')} | {est:.4f} | {act:.4f} | {ack:.4f} | {f'{ratio:.2f}' if ratio is not None else '—'} | {status} |")
    lines += ["", f"**Total actual: ${sum(actual_by_ep.values()):.4f}** · total estimated: ${sum(est_by_ep.values()):.4f}", "",
              "## Per endpoint per day (actual)", "", "| day (UTC) | endpoint | name | total $ | gpu $ | billed hours |", "|---|---|---|---|---|---|"]
    lines += [f"| {day} | {ep} | {names.get(ep, '')} | {float(total or 0):.4f} | {float(gpu or 0):.4f} | {n} |" for ep, day, total, gpu, n in daily]
    lines += ["", "## What ran (campaign/runs.csv)", "", "| date (UTC) | cell | endpoint | n_cold | est $ | note |", "|---|---|---|---|---|---|"]
    lines += [f"| {r.get('date_utc','')} | {r.get('cell','')} | {r.get('endpoint_id','')} | {r.get('n_cold','')} | {r.get('est_usd','')} | {r.get('note','')} |" for r in runs]
    if acks:
        lines += ["", "## Acknowledged overruns (campaign/spend_ack.csv)", "", "| date (UTC) | endpoint | $ | reason |", "|---|---|---|---|"]
        lines += [f"| {r.get('date_utc','')} | {r.get('endpoint_id','')} | {r.get('usd','')} | {r.get('reason','')} |" for r in acks]
    if estimates:
        lines += ["", "## Approved estimate (campaign/estimate.csv)", "", "| cell | est $ (total) |", "|---|---|"]
        lines += [f"| {e.get('cell','')} | {e.get('est_usd_total','')} |" for e in estimates]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"spend: actual ${sum(actual_by_ep.values()):.4f} across {len(actual_by_ep)} endpoint(s); estimated ${sum(est_by_ep.values()):.4f} → {args.out.relative_to(REPO_ROOT)}")
    for ep, est, act in overruns:
        print(f"  OVERRUN {ep}: actual (less acknowledged) ${act:.4f} > estimate ${est:.4f} × 1.2 — stop and review", file=sys.stderr)
    return 1 if (args.check and overruns) else 0


if __name__ == "__main__":
    sys.exit(main())
