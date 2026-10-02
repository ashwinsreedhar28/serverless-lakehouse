#!/usr/bin/env python3
"""Pack the reviewable surface of the repo into one markdown file for an external code audit.

    scripts/audit_bundle.py [--out audit/serverless-lakehouse-bundle.md]

Includes every tracked text file except the landing data itself (2.6 MB of logs and CSVs); for those it
includes the manifest plus the first 25 lines of one file per dataset, so a reviewer can see each format
without reading 9,000 log lines. Also includes the git log and the tracked-file tree.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_SUFFIX = {".png", ".jpg", ".pdf", ".parquet", ".pyc"}
SAMPLE_LINES = 25

# one representative per landing dataset (format sample only)
LANDING_SAMPLES = [
    "data/landing/emberserve/results/serverless_coldstart_pagedserve_slim_qwen3_8b_4090_graphsfirst.json",
    "data/landing/emberserve/results/runpod_serverless_7b_pagedserve_kv380.json",
    "data/landing/emberserve/results/serverless_coldstart_vllm_qwen3_8b_worker_log.txt",
    "data/landing/pulse/bench/logs/run2_cold_worker.log",
    "data/landing/pulse/bench/logs/vol_nocache_cycle1_cachehit_worker.log",
    "data/landing/pulse/results.csv",
    "data/landing/pulse/results_throughput.csv",
    "data/landing/pulse/bench/quality.csv",
    "data/landing/pulse/bench/quality_batches.csv",
]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def lang(p: Path) -> str:
    return {".py": "python", ".md": "markdown", ".html": "html", ".yml": "yaml", ".yaml": "yaml", ".csv": "csv",
            ".json": "json", ".txt": "text", ".toml": "toml", ".cfg": "ini", "": "text"}.get(p.suffix, "text")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "audit" / "serverless-lakehouse-bundle.md")
    a = ap.parse_args()

    files = [f for f in git("ls-files").splitlines() if f]
    head = git("rev-parse", "--short", "HEAD").strip()
    parts = [f"# serverless-lakehouse — audit bundle (git {head})\n",
             "Everything tracked except the landing data (format samples only) and binary files. Paths are repo-relative.\n",
             "## Tracked files\n\n```\n" + "\n".join(files) + "\n```\n",
             "## Git log\n\n```\n" + git("log", "--oneline", "--no-decorate") + "```\n"]
    full, sampled, skipped = 0, 0, 0
    for rel in files:
        p = ROOT / rel
        if p.suffix in SKIP_SUFFIX or rel.startswith("space/data/"):
            skipped += 1
            continue
        if rel.startswith("data/landing/") and rel != "data/landing/manifest.json":
            if rel not in LANDING_SAMPLES:
                skipped += 1
                continue
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            body = "\n".join(l[:400] for l in lines[:SAMPLE_LINES])
            parts.append(f"## {rel}  (format sample: first {min(SAMPLE_LINES, len(lines))} of {len(lines)} lines)\n\n```{lang(p)}\n{body}\n```\n")
            sampled += 1
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if rel == "docs/dashboard.html":
            text = text.split("const GOLD = ")[0] + "const GOLD = /* embedded gold JSON omitted from the bundle; see docs/gold_report.md */ null;"
        parts.append(f"## {rel}\n\n```{lang(p)}\n{text.rstrip()}\n```\n")
        full += 1
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {a.out.relative_to(ROOT)}: {full} files in full, {sampled} landing samples, {skipped} skipped, "
          f"{a.out.stat().st_size / 1024:.0f} KB (~{a.out.stat().st_size // 4 // 1000}k tokens)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
