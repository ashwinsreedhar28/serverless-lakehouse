#!/usr/bin/env python3
"""Create, pause, resume and delete Serverless endpoints through the Runpod REST API v2 — the few operations the
measurement campaign and the load generator need, with every cost-relevant setting explicit on the command line.

    python tools/runpod_endpoint.py catalog [--gpu "RTX 4090"]        pool ids and type ids, with $/hr and availability
    python tools/runpod_endpoint.py create --name … --image … --gpu "NVIDIA GeForce RTX 4090" --flashboot OFF \
            [--idle 10] [--max 1] [--disk 40] [--env K=V …] [--timeout-ms 600000]      → prints the endpoint id
    python tools/runpod_endpoint.py off <id>        workers.max = 0 (kill switch: nothing can start, nothing is billed)
    python tools/runpod_endpoint.py on <id> [--max 1]
    python tools/runpod_endpoint.py delete <id>     the end-of-stage rule: every campaign endpoint is deleted, not paused
    python tools/runpod_endpoint.py show <id>

Needs RUNPOD_API_KEY_RW (a key with write permission; the read-only RUNPOD_API_KEY cannot create or delete). Every
endpoint this tool creates is named `lh-…` and tagged in `env.LAKEHOUSE=1`, so `list --mine` and the spend log can tell
them from anything else on the account. `--gpu` takes a GPU *type* name as the catalog prints it; the tool maps it to
the pool that holds it and excludes the pool's other types, so "A40" really means an A40, not "whatever is in AMPERE_48".
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

REST = "https://api.runpod.io"


def key() -> str:
    k = os.environ.get("RUNPOD_API_KEY_RW")
    if not k:
        sys.exit("RUNPOD_API_KEY_RW is not set (a Runpod key with write permission; keep it out of the repo)")
    return k


def call(method: str, path: str, body: dict | None = None) -> dict | list:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(REST + path, data=data, method=method,
                                 headers={"Authorization": f"Bearer {key()}", "Content-Type": "application/json",
                                          "Accept": "application/json", "User-Agent": "serverless-lakehouse/runpod_endpoint"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            txt = r.read().decode()
            return json.loads(txt) if txt.strip() else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} → {e.code}: {e.read().decode(errors='replace')[:500]}")


def catalog(filter_text: str | None = None) -> list[dict]:
    out = call("GET", "/v2/catalog/gpus?product=SERVERLESS")
    gpus = out.get("gpus", out) if isinstance(out, dict) else out
    rows = []
    for g in gpus:
        name = g.get("displayName") or g.get("name") or g.get("id")
        if filter_text and filter_text.lower() not in json.dumps(g).lower():
            continue
        rows.append({"id": g.get("id"), "name": name, "pool": g.get("pool") or g.get("poolId"),
                     "memory_gb": g.get("memoryInGb") or g.get("memory"),
                     "price_hr": (g.get("pricing") or {}).get("serverless") or g.get("serverlessPrice") or g.get("price"),
                     "raw": g})
    return rows


def resolve_gpu(type_name: str) -> tuple[str, list[str], dict]:
    """GPU type name → (pool id, other type ids in that pool to exclude, the catalog row)."""
    rows = catalog()
    match = [r for r in rows if r["id"] == type_name or (r["name"] or "").lower() == type_name.lower()]
    if not match:
        match = [r for r in rows if type_name.lower() in (r["name"] or "").lower()]
    if len(match) != 1:
        names = sorted({r["name"] for r in match}) if match else sorted({r["name"] for r in rows})
        sys.exit(f"--gpu {type_name!r} matched {len(match)} catalog entries; use one of: {names}")
    g = match[0]
    others = [r["id"] for r in rows if r["pool"] == g["pool"] and r["id"] != g["id"]]
    return g["pool"], others, g


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("catalog"); p.add_argument("--gpu", default=None)
    p = sub.add_parser("create")
    p.add_argument("--name", required=True)
    p.add_argument("--image", required=True)
    p.add_argument("--gpu", required=True, help='GPU type as the catalog names it, e.g. "NVIDIA GeForce RTX 4090", "NVIDIA A40"')
    p.add_argument("--flashboot", required=True, choices=["OFF", "FLASHBOOT", "PRIORITY_FLASHBOOT"])
    p.add_argument("--idle", type=int, default=10, help="idle timeout seconds (billed)")
    p.add_argument("--max", type=int, default=1, help="max workers")
    p.add_argument("--disk", type=int, default=40, help="container disk GB")
    p.add_argument("--timeout-ms", type=int, default=600_000)
    p.add_argument("--env", action="append", default=[], help="K=V, repeatable")
    p.add_argument("--data-center", action="append", default=[], help="restrict placement, repeatable")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("off"); p.add_argument("id")
    p = sub.add_parser("on"); p.add_argument("id"); p.add_argument("--max", type=int, default=1)
    p = sub.add_parser("delete"); p.add_argument("id")
    p = sub.add_parser("show"); p.add_argument("id")
    p = sub.add_parser("list"); p.add_argument("--mine", action="store_true", help="only endpoints this tool created (env.LAKEHOUSE=1)")
    a = ap.parse_args(argv)

    if a.cmd == "catalog":
        for r in catalog(a.gpu):
            print(f"  {str(r['pool']):<14} {str(r['id']):<36} {str(r['name']):<32} {r['memory_gb']} GB  ${r['price_hr']}/hr")
        return 0
    if a.cmd == "create":
        pool, exclude, g = resolve_gpu(a.gpu)
        env = {"LAKEHOUSE": "1"}
        for kv in a.env:
            k, _, v = kv.partition("=")
            env[k] = v
        body = {
            "name": a.name if a.name.startswith("lh-") else f"lh-{a.name}",
            "type": "QUEUE",
            "image": a.image,
            "gpu": {"pools": [pool], "excludedTypes": exclude, "count": 1},
            "workers": {"min": 0, "max": a.max, "idleTimeout": a.idle},
            "scaling": {"type": "QUEUE_DELAY", "queueDelay": 4},
            "flashboot": a.flashboot,
            "disk": a.disk,
            "env": env,
            "timeout": a.timeout_ms,
        }
        if a.data_center:
            body["dataCenterIds"] = a.data_center
        print(json.dumps(body, indent=1), file=sys.stderr)
        print(f"  gpu {g['name']} in pool {pool} (${g['price_hr']}/hr), excluding {exclude}", file=sys.stderr)
        if a.dry_run:
            return 0
        ep = call("POST", "/v2/serverless", body)
        print(ep.get("id"))
        print(f"created {ep.get('id')} {ep.get('name')}", file=sys.stderr)
        return 0
    if a.cmd == "off":
        ep = call("PATCH", f"/v2/serverless/{a.id}", {"workers": {"min": 0, "max": 0}})
        print(f"{a.id}: workers.max = {ep.get('workers', {}).get('max')} (off)")
        return 0
    if a.cmd == "on":
        ep = call("PATCH", f"/v2/serverless/{a.id}", {"workers": {"min": 0, "max": a.max}})
        print(f"{a.id}: workers.max = {ep.get('workers', {}).get('max')}")
        return 0
    if a.cmd == "delete":
        call("DELETE", f"/v2/serverless/{a.id}")
        print(f"deleted {a.id}")
        return 0
    if a.cmd == "show":
        print(json.dumps(call("GET", f"/v2/serverless/{a.id}"), indent=1))
        return 0
    if a.cmd == "list":
        out = call("GET", "/v2/serverless?limit=1000")
        for ep in out.get("endpoints", []):
            if a.mine and (ep.get("env") or {}).get("LAKEHOUSE") != "1":
                continue
            w = ep.get("workers") or {}
            print(f"  {ep['id']:<16} {ep['name']:<40} max={w.get('max')} idle={w.get('idleTimeout')} flashboot={ep.get('flashboot')} pools={(ep.get('gpu') or {}).get('pools')}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
