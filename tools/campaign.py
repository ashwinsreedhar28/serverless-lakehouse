#!/usr/bin/env python3
"""Measurement campaign: GPU × FlashBoot × image, a few cold starts per cell spread over time of day, through the existing
cold-start script and the existing landing path. Nothing here runs load code of its own.

    python tools/campaign.py plan                    price the grid from campaign/grid.json → campaign/estimate.csv (no API)
    python tools/campaign.py create [--cells …]      one endpoint per cell, cloned from the cell's reference endpoint
                                                     (image, env, disk, timeout, CUDA) with the cell's GPU / FlashBoot;
                                                     max workers 1, min 0, idle timeout 5 s; seeds/coldstart_series.csv gets
                                                     one row per cell (GPU, FlashBoot, image known at run time, source "campaign")
    python tools/campaign.py slot [--n-cold 1]       one slot: every cell gets --n-cold cold starts (cells run concurrently,
                                                     each against its own endpoint), results → data/sources/runpod/campaign/,
                                                     campaign/runs.csv gets a row per cell, then the 20 % spend check
    python tools/campaign.py status                  endpoints, cold starts done per cell, $ so far
    python tools/campaign.py teardown                DELETE every campaign endpoint (the end-of-stage rule)
    python tools/campaign.py park                    workers.max = 0 on every campaign endpoint (nothing can start; keep configs)
    python tools/campaign.py unpark                  workers.max = 1 again

A cold request waits up to 45 min (--timeout-s 2700): a long placement wait on a saturated pool, or a 27 GB image pull onto
a host that has never seen it (seen 2026-10-07: US 4090 hosts full, Runpod placed in EUR-IS-1 and pulled for 37+ min), is a
result (`delay_ms`, and `schedule_pull_create` in the timeline phases), not a failure. Throttled and initializing workers are
not billed.

Keys: RUNPOD_API_KEY_RW (write). Cells and prices live in campaign/grid.json; `plan` is the estimate you approve before
`create`. `slot` refuses to run when the spend check fails, when a cell has already reached its planned cold starts, or
when campaign/endpoints.json is missing. Schedule slots with launchd (campaign/launchd.plist.example) or by hand.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CAMPAIGN = REPO / "campaign"
GRID = CAMPAIGN / "grid.json"
ENDPOINTS = CAMPAIGN / "endpoints.json"
RUNS = CAMPAIGN / "runs.csv"
ESTIMATE = CAMPAIGN / "estimate.csv"
OUT_DIR = REPO / "data" / "sources" / "runpod" / "campaign"
SEEDS = REPO / "seeds" / "coldstart_series.csv"
COLDSTART = REPO / "tools" / "serverless_coldstart.py"

sys.path.insert(0, str(REPO / "tools"))
import runpod_endpoint as rp  # noqa: E402


def grid() -> dict:
    return json.loads(GRID.read_text(encoding="utf-8"))


def cells(g: dict, only: list[str] | None = None) -> list[dict]:
    out = []
    for gpu in g["gpus"]:
        for fb in g["flashboot"]:
            for img in g["images"]:
                cell = f"{gpu['slug']}_{'fbon' if fb == 'FLASHBOOT' else 'fboff'}_{img['slug']}"
                if only and cell not in only:
                    continue
                boot_s = img["boot_s"] if fb != "FLASHBOOT" else img["boot_s"]     # FlashBoot hits make it cheaper, not dearer
                billed_s = boot_s + img["exec_s"] + g["idle_timeout_s"]
                per_cold = billed_s / 3600 * gpu["usd_per_hr"]
                out.append({"cell": cell, "gpu": gpu, "flashboot": fb, "image": img, "billed_s_per_cold": billed_s,
                            "usd_per_cold": per_cold, "n_cold": g["n_cold_per_cell"],
                            "usd_total": per_cold * g["n_cold_per_cell"] * g["retry_allowance"]})
    return out


def cmd_plan(a) -> int:
    g = grid()
    rows = cells(g)
    print(f"{'cell':<28} {'$/hr':>5} {'billed s/cold':>13} {'$/cold':>7} {'n':>3} {'$ total (×' + str(g['retry_allowance']) + ')':>16}")
    for c in rows:
        print(f"{c['cell']:<28} {c['gpu']['usd_per_hr']:>5.2f} {c['billed_s_per_cold']:>13.0f} {c['usd_per_cold']:>7.3f} {c['n_cold']:>3} {c['usd_total']:>16.2f}")
    total = sum(c["usd_total"] for c in rows)
    print(f"{'TOTAL':<28} {'':>5} {'':>13} {'':>7} {sum(c['n_cold'] for c in rows):>3} {total:>16.2f}")
    with ESTIMATE.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cell", "gpu_type", "usd_per_hr", "flashboot", "image", "billed_s_per_cold", "usd_per_cold", "n_cold", "est_usd_total"])
        for c in rows:
            w.writerow([c["cell"], c["gpu"]["type"], c["gpu"]["usd_per_hr"], c["flashboot"], c["image"]["slug"],
                        round(c["billed_s_per_cold"]), round(c["usd_per_cold"], 4), c["n_cold"], round(c["usd_total"], 2)])
    print(f"→ {ESTIMATE.relative_to(REPO)}; cap {g['usd_cap']} → {'OK' if total <= g['usd_cap'] else 'OVER THE CAP: cut the grid'}")
    return 0 if total <= g["usd_cap"] else 1


def load_endpoints() -> dict:
    return json.loads(ENDPOINTS.read_text(encoding="utf-8")) if ENDPOINTS.is_file() else {}


def save_endpoints(d: dict) -> None:
    ENDPOINTS.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")


def seed_row(c: dict, endpoint_id: str) -> list[str]:
    img = c["image"]
    return [c["cell"], img["engine"], img.get("engine_build", ""), img["model"], c["gpu"]["gpu_model"],
            "on" if c["flashboot"] == "FLASHBOOT" else "off", "api (endpoint config, campaign)", img["weights_mode"],
            str(img.get("image_gb", "")), f"campaign cell; endpoint {endpoint_id}; {img['note']}"]


def cmd_create(a) -> int:
    g = grid()
    eps = load_endpoints()
    refs: dict[str, dict] = {}
    for c in cells(g, a.cells):
        if c["cell"] in eps and a.recreate and not a.dry_run:
            rp.call("DELETE", f"/v2/serverless/{eps[c['cell']]['endpoint_id']}")
            print(f"  {c['cell']}: deleted {eps[c['cell']]['endpoint_id']}")
            del eps[c["cell"]]
            save_endpoints(eps)
        if c["cell"] in eps:
            print(f"  {c['cell']}: already {eps[c['cell']]['endpoint_id']}")
            continue
        ref_id = c["image"]["reference_endpoint"]
        ref = refs.setdefault(ref_id, rp.call("GET", f"/v2/serverless/{ref_id}"))
        pool, exclude, gcat = rp.resolve_gpu(c["gpu"]["type"])
        env = dict(ref.get("env") or {})
        env.update(c["image"].get("env", {}))
        env["LAKEHOUSE"] = "1"
        env["LAKEHOUSE_CELL"] = c["cell"]
        body = {
            "name": f"lh-camp-{c['cell']}",
            "type": "QUEUE",
            # the image is Runpod's own GitHub build in registry.runpod.net; only its template can pull it ("Failed to get Hub
            # registry auth" otherwise), so create from the template and override the rest
            "templateId": c["image"]["template_id"],
            "gpu": {"pools": [pool], "excludedTypes": exclude, "count": 1,
                    **({"allowedCudaVersions": ref["gpu"]["allowedCudaVersions"]} if (ref.get("gpu") or {}).get("allowedCudaVersions") else {}),
                    **({"minCudaVersion": ref["gpu"]["minCudaVersion"]} if (ref.get("gpu") or {}).get("minCudaVersion") and not (ref.get("gpu") or {}).get("allowedCudaVersions") else {})},
            "workers": {"min": 0, "max": 1, "idleTimeout": g["idle_timeout_s"]},
            "scaling": {"type": "QUEUE_DELAY", "queueDelay": 4},
            "flashboot": c["flashboot"],
            "disk": ref.get("disk") or 40,
            "env": env,
            "timeout": ref.get("timeout") or 600000,
        }
        if a.dry_run:
            print(json.dumps(body, indent=1))
            continue
        ep = rp.call("POST", "/v2/serverless", body)
        eps[c["cell"]] = {"endpoint_id": ep["id"], "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                          "gpu_type": c["gpu"]["type"], "pool": pool, "flashboot": c["flashboot"], "image": ref["image"],
                          "usd_per_hr": c["gpu"]["usd_per_hr"], "usd_per_cold": round(c["usd_per_cold"], 4), "n_cold_planned": c["n_cold"]}
        save_endpoints(eps)
        if c["cell"] not in SEEDS.read_text(encoding="utf-8"):
            with SEEDS.open("a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(seed_row(c, ep["id"]))
        print(f"  {c['cell']}: created {ep['id']} ({gcat['name']} in {pool}, flashboot {c['flashboot']}) from template {c['image']['template_id']}")
    return 0


def cold_starts_done(cell: str) -> int:
    n = 0
    for p in OUT_DIR.glob(f"serverless_coldstart_{cell}_*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        n += sum(1 for r in d.get("runs", []) if r["cold"].get("ok") and r["cold"].get("cold"))
    return n


def run_cell(cell: str, ep: dict, n_cold: int, key: str, timeline: bool, stamp: str) -> tuple[str, int, str]:
    out = OUT_DIR / f"serverless_coldstart_{cell}_{stamp}.json"
    cmd = [sys.executable, str(COLDSTART), "--mode", "queue", "--endpoint", ep["endpoint_id"], "--api-key", key,
           "--repeats", str(n_cold), "--idle-s", "0", "--zero-wait-s", "300", "--max-tokens", "16", "--timeout-s", "2700",
           "--label", cell, "--image", ep["image"], "--note", f"campaign slot {stamp}; {ep['gpu_type']}; flashboot {ep['flashboot']}",
           "--out", str(out)]
    if timeline:
        cmd.append("--timeline")
    r = subprocess.run(cmd, capture_output=True, text=True)
    tail = (r.stderr or "").strip().splitlines()[-1:] or [""]
    return cell, r.returncode, tail[0]


def cmd_slot(a) -> int:
    key = os.environ.get("RUNPOD_API_KEY_RW") or sys.exit("RUNPOD_API_KEY_RW is not set")
    g = grid()
    eps = load_endpoints()
    if not eps:
        sys.exit("campaign/endpoints.json is missing: run `campaign.py create` first")
    if not a.skip_spend_check:
        chk = subprocess.run([sys.executable, "-m", "lakehouse.sf.spend", "--check"], cwd=REPO)
        if chk.returncode != 0:
            sys.exit("spend check failed (actual > estimate × 1.2 on some endpoint): slot not run")
    todo = []
    for cell, ep in eps.items():
        if a.cells and cell not in a.cells:
            continue
        done = cold_starts_done(cell)
        if done >= ep["n_cold_planned"]:
            print(f"  {cell}: {done}/{ep['n_cold_planned']} cold starts already, skipping")
            continue
        todo.append((cell, ep))
    if not todo:
        print("slot: nothing to do")
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img_by_slug = {i["slug"]: i for i in g["images"]}
    print(f"slot {stamp}: {len(todo)} cells × {a.n_cold} cold start(s), concurrently")
    with ThreadPoolExecutor(max_workers=min(8, len(todo))) as pool:
        futs = [pool.submit(run_cell, cell, ep, a.n_cold, key, img_by_slug[cell.rsplit('_', 1)[-1]].get("timeline", False), stamp)
                for cell, ep in todo]
        results = [f.result() for f in futs]
    new = not RUNS.is_file()
    with RUNS.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date_utc", "cell", "endpoint_id", "n_cold", "est_usd", "note"])
        for cell, rc, tail in results:
            ep = eps[cell]
            w.writerow([stamp, cell, ep["endpoint_id"], a.n_cold, round(ep["usd_per_cold"] * a.n_cold, 4), f"rc={rc} {tail[:120]}"])
            print(f"  {cell:<28} rc={rc}  {tail[:110]}")
    subprocess.run([sys.executable, "-m", "lakehouse.land", "--only", "runpod"], cwd=REPO, check=False)
    return 0 if all(rc == 0 for _, rc, _ in results) else 1


def cmd_park(a, max_workers: int = 0) -> int:
    for cell, ep in load_endpoints().items():
        if ep.get("deleted_at"):
            continue
        rp.call("PATCH", f"/v2/serverless/{ep['endpoint_id']}", {"workers": {"min": 0, "max": max_workers}})
        print(f"  {cell}: workers.max = {max_workers}")
    return 0


def cmd_status(a) -> int:
    eps = load_endpoints()
    for cell, ep in eps.items():
        print(f"  {cell:<28} {ep['endpoint_id']}  {cold_starts_done(cell)}/{ep['n_cold_planned']} cold starts  est ${ep['usd_per_cold']:.3f}/cold")
    if RUNS.is_file():
        rows = list(csv.DictReader(RUNS.open(encoding="utf-8")))
        print(f"  {len(rows)} slot-cell runs logged, est ${sum(float(r['est_usd']) for r in rows):.2f}")
    return 0


def cmd_teardown(a) -> int:
    eps = load_endpoints()
    for cell, ep in list(eps.items()):
        rp.call("DELETE", f"/v2/serverless/{ep['endpoint_id']}")
        ep["deleted_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"  deleted {ep['endpoint_id']} ({cell})")
    save_endpoints(eps)
    left = [e for e in rp.call("GET", "/v2/serverless?limit=1000").get("endpoints", []) if (e.get("env") or {}).get("LAKEHOUSE_CELL")]
    print(f"teardown: {len(left)} campaign endpoint(s) still on the account")
    return 0 if not left else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    p = sub.add_parser("create"); p.add_argument("--cells", nargs="*"); p.add_argument("--dry-run", action="store_true")
    p.add_argument("--recreate", action="store_true", help="DELETE the cell's existing endpoint first (a broken one), then create")
    p = sub.add_parser("slot"); p.add_argument("--n-cold", type=int, default=1); p.add_argument("--cells", nargs="*")
    p.add_argument("--skip-spend-check", action="store_true")
    sub.add_parser("status")
    sub.add_parser("teardown")
    sub.add_parser("park")
    sub.add_parser("unpark")
    a = ap.parse_args(argv)
    return {"plan": cmd_plan, "create": cmd_create, "slot": cmd_slot, "status": cmd_status, "teardown": cmd_teardown,
            "park": cmd_park, "unpark": lambda a: cmd_park(a, 1)}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
