#!/usr/bin/env python3
"""Snapshot the Runpod account through the REST API v2 and PUT the snapshot to the Snowflake stage @RUNPOD.

    python tools/runpod_poll.py [--out data/runpod] [--no-upload] [--jobs-file data/runpod/jobs.jsonl]

What the API exposes (verified against api.runpod.io/v2, Oct 2026), and what one poll writes:
  GET /v2/serverless                         endpoint configs: id, name, type, gpu pools, workers min/max/idleTimeout,
                                             scaling, flashboot (OFF | FLASHBOOT | PRIORITY_FLASHBOOT), image, createdAt
  GET /v2/serverless/{id}/workers            the *active* workers right now (id, status, gpuTypeId, dataCenterId, startedAt,
                                             uptimeSeconds, image, config version); scaled-down workers are gone
  GET /v2/serverless/{id}/releases           release history (config changes, rollout status)
  GET api.runpod.ai/v2/{id}/health           the endpoint's job counters (completed/failed/inProgress/inQueue/retried)
                                             and worker counts (idle/initializing/ready/running/throttled/unhealthy)
  GET /v2/billing/serverless?bucketSize=hour&lastN=48    $ per endpoint per hour (GPU/CPU/disk)
  GET api.runpod.ai/v2/{id}/status/{job}     per-job delayTime / executionTime / workerId / status — only for job ids the
                                             caller knows (--jobs-file), and only within 30 min of completion

There is no "list jobs" endpoint and no REST equivalent of the console's Metrics tab (percentiles, cold-start counts), so
worker *events* have to be derived downstream by diffing consecutive worker snapshots (silver_runpod_worker_events), and
job-level data exists only for jobs whose ids were written to --jobs-file by the thing that submitted them.

One poll = one JSON document, data/runpod/polls/<UTC>.json, named with its own sha256 in the stage path like every other
landed file (@RUNPOD/<sha12>/polls/<name>.json). PUT needs no warehouse; the COPY INTO + dbt step runs separately
(`python -m lakehouse.sf.runpod load`, or the runpod-load GitHub workflow) so a 30-minute poll cadence does not resume the
warehouse 48 times a day. RUNPOD_API_KEY is read from the environment (a read-only key is enough).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REST = "https://api.runpod.io"
JOBS = "https://api.runpod.ai"
REPO_ROOT = Path(__file__).resolve().parent.parent


def get(url: str, key: str, timeout: int = 30) -> dict | list | None:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}", "Accept": "application/json",
                                               "User-Agent": "serverless-lakehouse/runpod_poll"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code == 429 and attempt < 2:
                time.sleep(int(e.headers.get("Retry-After", "5")))
                continue
            print(f"  {e.code} {url}: {body}", file=sys.stderr)
            return {"_error": e.code, "_detail": body}
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 2:
                time.sleep(2)
                continue
            print(f"  {url}: {e}", file=sys.stderr)
            return {"_error": str(e)}
    return None


def list_endpoints(key: str) -> list[dict]:
    out, cursor = [], None
    while True:
        url = f"{REST}/v2/serverless?limit=1000" + (f"&cursor={cursor}" if cursor else "")
        page = get(url, key)
        if not isinstance(page, dict) or "endpoints" not in page:
            print(f"  endpoints: unexpected response {str(page)[:200]}", file=sys.stderr)
            return out
        out += page["endpoints"]
        pg = page.get("pagination") or {}
        cursor = pg.get("nextCursor")
        if not pg.get("hasNextPage") or not cursor:
            return out


def read_jobs_file(path: Path, polled_at: datetime) -> list[dict]:
    """{endpoint_id, job_id, submitted_at} lines written by whatever submits jobs; only the last 35 minutes are worth asking about."""
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            j = json.loads(line)
            t = datetime.fromisoformat(j["submitted_at"].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            continue
        if polled_at - t <= timedelta(minutes=35):
            out.append(j)
    return out


def poll(key: str, jobs: list[dict]) -> dict:
    polled_at = datetime.now(timezone.utc)
    doc: dict = {"polled_at": polled_at.isoformat(timespec="seconds"), "tool": "runpod_poll 0.1", "endpoints": [],
                 "workers": {}, "health": {}, "releases": {}, "billing": None, "jobs": []}
    endpoints = list_endpoints(key)
    doc["endpoints"] = endpoints
    for ep in endpoints:
        eid = ep.get("id")
        if not eid:
            continue
        doc["workers"][eid] = get(f"{REST}/v2/serverless/{eid}/workers", key)
        doc["releases"][eid] = get(f"{REST}/v2/serverless/{eid}/releases", key)
        doc["health"][eid] = get(f"{JOBS}/v2/{eid}/health", key)
    doc["billing"] = get(f"{REST}/v2/billing/serverless?bucketSize=hour&lastN=48", key)
    for j in jobs:
        st = get(f"{JOBS}/v2/{j['endpoint_id']}/status/{j['job_id']}", key)
        doc["jobs"].append({"endpoint_id": j["endpoint_id"], "job_id": j["job_id"], "submitted_at": j.get("submitted_at"), "status": st})
    return doc


def write_snapshot(doc: dict, out_dir: Path) -> tuple[Path, str]:
    polls = out_dir / "polls"
    polls.mkdir(parents=True, exist_ok=True)
    name = doc["polled_at"].replace(":", "").replace("+0000", "Z") + ".json"
    path = polls / name
    data = json.dumps(doc, separators=(",", ":"), sort_keys=True).encode("utf-8")
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "runpod")
    ap.add_argument("--jobs-file", type=Path, default=REPO_ROOT / "data" / "runpod" / "jobs.jsonl")
    ap.add_argument("--no-upload", action="store_true", help="write the snapshot locally only (no Snowflake)")
    args = ap.parse_args(argv)

    key = os.environ.get("RUNPOD_API_KEY")
    if not key:
        print("RUNPOD_API_KEY is not set", file=sys.stderr)
        return 2
    doc = poll(key, read_jobs_file(args.jobs_file, datetime.now(timezone.utc)))
    path, sha = write_snapshot(doc, args.out)
    n_workers = sum(len((w or {}).get("workers") or []) for w in doc["workers"].values() if isinstance(w, dict))
    print(f"runpod_poll: {len(doc['endpoints'])} endpoints, {n_workers} active workers, "
          f"{len(doc['jobs'])} job look-ups, billing {'ok' if isinstance(doc['billing'], dict) and 'records' in doc['billing'] else 'n/a'} "
          f"→ {path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path} sha={sha[:12]}")
    if args.no_upload:
        return 0
    sys.path.insert(0, str(REPO_ROOT))
    from lakehouse.sf.runpod import put_snapshot

    status = put_snapshot(path, sha)
    print(f"  PUT @RUNPOD/{sha[:12]}/polls/{path.name}: {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
