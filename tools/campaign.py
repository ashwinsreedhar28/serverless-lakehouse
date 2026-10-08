#!/usr/bin/env python3
"""Measurement campaign: GPU × FlashBoot × image, a few cold starts per cell spread over time of day, through the existing
cold-start script and the existing landing path. Nothing here runs load code of its own.

    python tools/campaign.py plan                    price the grid from campaign/grid.json → campaign/estimate.csv (no API)
    python tools/campaign.py prepare                 record each image's endpoint (the one Runpod built from GitHub) and its
                                                     original config into campaign/endpoints.json; seeds/coldstart_series.csv
                                                     gets one row per cell (GPU, FlashBoot, image known at run time)
    python tools/campaign.py slot [--n-cold 1]       one slot: for every image (concurrently), for every GPU × FlashBoot cell
                                                     (sequentially): PATCH the endpoint to the cell's pool + FlashBoot, max workers 1,
                                                     run --n-cold cold starts, max workers 0; results → data/sources/runpod/campaign/,
                                                     campaign/runs.csv gets a row per cell, then land --only runpod + the 20 % spend check
    python tools/campaign.py status                  cold starts done per cell, $ so far
    python tools/campaign.py park / unpark           workers.max 0 / 1 on the three endpoints
    python tools/campaign.py restore                 the end-of-stage rule: original pool / FlashBoot / idle timeout / max 0 back on
                                                     each endpoint, and DELETE any lh-camp-* endpoint left from earlier attempts

Why endpoints are reused, not created: the images are Runpod's own GitHub builds in registry.runpod.net, and only the endpoint
Runpod built can pull them (a new endpoint with the same image — or the same template — fails with "Failed to get Hub registry
auth"; seen 2026-10-07). PATCHing gpu.pools / excludedTypes / flashboot / workers on an existing endpoint is allowed and takes
effect on the next worker, which is always a fresh one here (max 0 between cells).

Keys: RUNPOD_API_KEY_RW (write). A cold request waits up to 45 min (--timeout-s 2700): a long placement wait on a saturated
pool, or a 27 GB image pull onto a host that has never seen it, is a result (`delay_ms`, and `schedule_pull_create` in the
timeline phases), not a failure. Throttled and initializing workers are not billed. Slots are serialised by a lock file so a
long slot and the next launchd firing cannot overlap.
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
LOCK = CAMPAIGN / ".slot.lock"
OUT_DIR = REPO / "data" / "sources" / "runpod" / "campaign"
SEEDS = REPO / "seeds" / "coldstart_series.csv"
COLDSTART = REPO / "tools" / "serverless_coldstart.py"

sys.path.insert(0, str(REPO / "tools"))
import runpod_endpoint as rp  # noqa: E402


def grid() -> dict:
    return json.loads(GRID.read_text(encoding="utf-8"))


def cells(g: dict, only: list[str] | None = None) -> list[dict]:
    out = []
    for img in g["images"]:
        for gpu in g["gpus"]:
            for fb in g["flashboot"]:
                cell = f"{gpu['slug']}_{'fbon' if fb == 'FLASHBOOT' else 'fboff'}_{img['slug']}"
                if only and cell not in only:
                    continue
                billed_s = img["boot_s"] + img["exec_s"] + g["idle_timeout_s"]      # FlashBoot hits make it cheaper, not dearer
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
        w.writerow(["cell", "gpu_type", "usd_per_hr", "flashboot", "image", "endpoint_id", "billed_s_per_cold", "usd_per_cold", "n_cold", "est_usd_total"])
        for c in rows:
            w.writerow([c["cell"], c["gpu"]["type"], c["gpu"]["usd_per_hr"], c["flashboot"], c["image"]["slug"], c["image"]["reference_endpoint"],
                        round(c["billed_s_per_cold"]), round(c["usd_per_cold"], 4), c["n_cold"], round(c["usd_total"], 2)])
    print(f"→ {ESTIMATE.relative_to(REPO)}; cap {g['usd_cap']} → {'OK' if total <= g['usd_cap'] else 'OVER THE CAP: cut the grid'}")
    return 0 if total <= g["usd_cap"] else 1


def load_endpoints() -> dict:
    return json.loads(ENDPOINTS.read_text(encoding="utf-8")) if ENDPOINTS.is_file() else {}


def save_endpoints(d: dict) -> None:
    ENDPOINTS.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")


def seed_row(c: dict) -> list[str]:
    img = c["image"]
    return [c["cell"], img["engine"], img.get("engine_build", ""), img["model"], c["gpu"]["gpu_model"],
            "on" if c["flashboot"] == "FLASHBOOT" else "off", "api (endpoint config, campaign)", img["weights_mode"],
            str(img.get("image_gb", "")), f"campaign cell on endpoint {img['reference_endpoint']}; {img['note']}"]


def cmd_prepare(a) -> int:
    g = grid()
    slugs = {img["slug"] for img in g["images"]}
    eps = {k: v for k, v in load_endpoints().items() if k in slugs and "original" in v}   # drop entries from the old per-cell design
    have = SEEDS.read_text(encoding="utf-8")
    for img in g["images"]:
        ep_id = img["reference_endpoint"]
        if img["slug"] not in eps:
            ep = rp.call("GET", f"/v2/serverless/{ep_id}")
            eps[img["slug"]] = {"endpoint_id": ep_id, "name": ep.get("name"), "image": ep.get("image"),
                                "original": {"gpu": {"pools": (ep.get("gpu") or {}).get("pools"), "excludedTypes": (ep.get("gpu") or {}).get("excludedTypes") or []},
                                             "flashboot": ep.get("flashboot"), "workers": ep.get("workers")},
                                "prepared_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            print(f"  {img['slug']:<8} {ep_id} {ep.get('name')}: original pools={eps[img['slug']]['original']['gpu']['pools']} "
                  f"flashboot={ep.get('flashboot')} workers={ep.get('workers')}")
        else:
            print(f"  {img['slug']:<8} {ep_id}: already recorded")
    save_endpoints(eps)
    n = 0
    with SEEDS.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for c in cells(g):
            if c["cell"] + "," not in have:
                w.writerow(seed_row(c))
                n += 1
    print(f"prepare: {len(eps)} endpoints recorded, {n} seed rows appended")
    return 0


def cold_starts_done(cell: str) -> int:
    n = 0
    for p in OUT_DIR.glob(f"serverless_coldstart_{cell}_*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        n += sum(1 for r in d.get("runs", []) if r["cold"].get("ok") and r["cold"].get("cold"))
    return n


def gpu_body(endpoint_id: str, pools: list[str], exclude: list[str]) -> dict:
    """The endpoint's CUDA constraint carried over explicitly: the API rejects a PATCH to `gpu` when the stored object has both
    allowedCudaVersions and minCudaVersion (console-made endpoints can), and `minCudaVersion: null` fails validation
    (422 "want string") — so send exactly one of the two keys and leave the other out."""
    cur = (rp.call("GET", f"/v2/serverless/{endpoint_id}").get("gpu") or {})
    body = {"pools": pools, "excludedTypes": exclude, "count": cur.get("count") or 1}
    if cur.get("minCudaVersion"):
        # The PATCH is merged into the stored object, so a stored list must be *emptied*, not omitted ([] passes the
        # mutual-exclusion check; null does not pass validation). worker-vllm stores ["13.0"] + "13.0" — keep the min.
        body["allowedCudaVersions"], body["minCudaVersion"] = [], cur["minCudaVersion"]
    elif cur.get("allowedCudaVersions"):
        body["allowedCudaVersions"] = cur["allowedCudaVersions"]
    return body


def set_cell(endpoint_id: str, c: dict, max_workers: int, idle_s: int) -> None:
    pool, exclude, _ = rp.resolve_gpu(c["gpu"]["type"])
    rp.call("PATCH", f"/v2/serverless/{endpoint_id}", {
        "gpu": gpu_body(endpoint_id, [pool], exclude),
        "flashboot": c["flashboot"],
        "workers": {"min": 0, "max": max_workers, "idleTimeout": idle_s},
    })


def wait_unpaused(endpoint_id: str, key: str, max_wait_s: int = 180) -> float:
    """After a 0→1 PATCH the job API can keep answering 409 ENDPOINT_PAUSED for a while (seen on the first cell of a lane after
    a long pause), and a cold request that hits it is lost while the warm one that follows becomes the real cold start.
    Wait for the control plane to report max=1, then probe a job route until it stops saying paused. Returns seconds waited."""
    import urllib.error
    import urllib.request
    t0 = time.time()
    while (rp.call("GET", f"/v2/serverless/{endpoint_id}").get("workers") or {}).get("max", 0) < 1:
        if time.time() - t0 > max_wait_s:
            sys.exit(f"{endpoint_id}: workers.max still 0 after {max_wait_s}s")
        time.sleep(5)
    while time.time() - t0 < max_wait_s:
        req = urllib.request.Request(f"{rp.JOBS}/v2/{endpoint_id}/status/campaign-probe",
                                     headers={"Authorization": f"Bearer {key}", "User-Agent": "serverless-lakehouse/campaign"})
        try:
            urllib.request.urlopen(req, timeout=30).read()
            break                                   # any non-error answer: the job API sees the endpoint as live
        except urllib.error.HTTPError as e:
            if e.code == 409 and b"ENDPOINT_PAUSED" in e.read():
                time.sleep(10)
                continue
            break                                   # 404 for the fake job id is the expected answer once unpaused
        except urllib.error.URLError:
            time.sleep(10)
    time.sleep(10)                                  # settle: the probe and the queue front-end are not the same cache
    return time.time() - t0


def run_cell(c: dict, ep: dict, n_cold: int, key: str, stamp: str, idle_s: int) -> tuple[str, int, str]:
    cell, endpoint_id = c["cell"], ep["endpoint_id"]
    set_cell(endpoint_id, c, 1, idle_s)
    waited = wait_unpaused(endpoint_id, key)
    print(f"  [{c['image']['slug']}] {cell}: unpaused after {waited:.0f}s", flush=True)
    out = OUT_DIR / f"serverless_coldstart_{cell}_{stamp}.json"
    cmd = [sys.executable, str(COLDSTART), "--mode", "queue", "--endpoint", endpoint_id, "--api-key", key,
           "--repeats", str(n_cold), "--idle-s", "0", "--zero-wait-s", "300", "--max-tokens", "16", "--timeout-s", "2700",
           "--label", cell, "--image", ep["image"], "--note", f"campaign slot {stamp}; {c['gpu']['type']}; flashboot {c['flashboot']}",
           "--out", str(out)]
    if c["image"].get("timeline"):
        cmd.append("--timeline")
    r = subprocess.run(cmd, capture_output=True, text=True)
    rp.call("PATCH", f"/v2/serverless/{endpoint_id}", {"workers": {"min": 0, "max": 0, "idleTimeout": idle_s}})
    tail = (r.stderr or "").strip().splitlines()[-1:] or [""]
    return cell, r.returncode, tail[0]


def run_image(img_slug: str, todo: list[dict], ep: dict, n_cold: int, key: str, stamp: str, idle_s: int) -> list[tuple[str, int, str]]:
    results = []
    for c in todo:
        print(f"  [{img_slug}] {c['cell']} …", flush=True)
        results.append(run_cell(c, ep, n_cold, key, stamp, idle_s))
        print(f"  [{img_slug}] {results[-1][0]:<28} rc={results[-1][1]}  {results[-1][2][:100]}", flush=True)
    return results


def cmd_slot(a) -> int:
    key = os.environ.get("RUNPOD_API_KEY_RW") or sys.exit("RUNPOD_API_KEY_RW is not set")
    g = grid()
    eps = load_endpoints()
    if not eps:
        sys.exit("campaign/endpoints.json is missing: run `campaign.py prepare` first")
    if LOCK.is_file() and time.time() - LOCK.stat().st_mtime < 6 * 3600:
        sys.exit(f"slot: another slot is running (lock {LOCK.relative_to(REPO)}, {int(time.time() - LOCK.stat().st_mtime)} s old)")
    if not a.skip_spend_check:
        chk = subprocess.run([sys.executable, "-m", "lakehouse.sf.spend", "--check"], cwd=REPO)
        if chk.returncode != 0:
            sys.exit("spend check failed (actual > estimate × 1.2 on some endpoint): slot not run")
    by_image: dict[str, list[dict]] = {}
    for c in cells(g, a.cells):
        done = cold_starts_done(c["cell"])
        if done >= c["n_cold"]:
            print(f"  {c['cell']}: {done}/{c['n_cold']} cold starts already, skipping")
            continue
        by_image.setdefault(c["image"]["slug"], []).append(c)
    if not by_image:
        print("slot: nothing to do")
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(stamp)
    try:
        print(f"slot {stamp}: {sum(len(v) for v in by_image.values())} cells × {a.n_cold} cold start(s); images concurrently, cells sequentially per image")
        with ThreadPoolExecutor(max_workers=len(by_image)) as pool:
            futs = [pool.submit(run_image, slug, todo, eps[slug], a.n_cold, key, stamp, g["idle_timeout_s"]) for slug, todo in by_image.items()]
            results = [r for f in futs for r in f.result()]
    finally:
        LOCK.unlink(missing_ok=True)
    cell_by_name = {c["cell"]: c for v in by_image.values() for c in v}
    new = not RUNS.is_file()
    with RUNS.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date_utc", "cell", "endpoint_id", "n_cold", "est_usd", "note"])
        for cell, rc, tail in results:
            c = cell_by_name[cell]
            w.writerow([stamp, cell, c["image"]["reference_endpoint"], a.n_cold, round(c["usd_per_cold"] * a.n_cold, 4), f"rc={rc} {tail[:120]}"])
    subprocess.run([sys.executable, "-m", "lakehouse.land", "--only", "runpod"], cwd=REPO, check=False)
    return 0 if all(rc == 0 for _, rc, _ in results) else 1


def cmd_status(a) -> int:
    g = grid()
    for c in cells(g):
        print(f"  {c['cell']:<28} {c['image']['reference_endpoint']}  {cold_starts_done(c['cell'])}/{c['n_cold']} cold starts  est ${c['usd_per_cold']:.3f}/cold")
    if RUNS.is_file():
        rows = list(csv.DictReader(RUNS.open(encoding="utf-8")))
        print(f"  {len(rows)} slot-cell runs logged, est ${sum(float(r['est_usd']) for r in rows):.2f}")
    return 0


def cmd_park(a, max_workers: int = 0) -> int:
    for slug, ep in load_endpoints().items():
        if "original" not in ep:
            continue
        rp.call("PATCH", f"/v2/serverless/{ep['endpoint_id']}", {"workers": {"min": 0, "max": max_workers}})
        print(f"  {slug}: {ep['endpoint_id']} workers.max = {max_workers}")
    return 0


def cmd_restore(a) -> int:
    for slug, ep in load_endpoints().items():
        if "original" not in ep:
            continue
        o = ep["original"]
        body = {"gpu": gpu_body(ep["endpoint_id"], o["gpu"]["pools"], o["gpu"]["excludedTypes"]), "flashboot": o["flashboot"],
                "workers": {"min": 0, "max": 0, "idleTimeout": (o.get("workers") or {}).get("idleTimeout", 5)}}
        rp.call("PATCH", f"/v2/serverless/{ep['endpoint_id']}", body)
        print(f"  {slug}: {ep['endpoint_id']} restored pools={o['gpu']['pools']} flashboot={o['flashboot']} max=0")
    left = [e for e in rp.call("GET", "/v2/serverless?limit=1000").get("endpoints", []) if e.get("name", "").startswith("lh-camp-")]
    for e in left:
        rp.call("DELETE", f"/v2/serverless/{e['id']}")
        print(f"  deleted leftover {e['id']} {e['name']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    sub.add_parser("prepare")
    p = sub.add_parser("slot"); p.add_argument("--n-cold", type=int, default=1); p.add_argument("--cells", nargs="*")
    p.add_argument("--skip-spend-check", action="store_true")
    sub.add_parser("status")
    sub.add_parser("park")
    sub.add_parser("unpark")
    sub.add_parser("restore")
    a = ap.parse_args(argv)
    return {"plan": cmd_plan, "prepare": cmd_prepare, "slot": cmd_slot, "status": cmd_status, "park": cmd_park,
            "unpark": lambda a: cmd_park(a, 1), "restore": cmd_restore}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
