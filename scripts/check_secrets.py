#!/usr/bin/env python3
"""Scan files for credentials using the same patterns `lakehouse.land` redacts with.

    scripts/check_secrets.py            # every git-tracked file + anything staged
    scripts/check_secrets.py --staged   # only staged content (what the pre-commit hook runs)
    scripts/check_secrets.py PATH...    # specific files or directories

Exit 1 on any hit. Matches are printed masked, never in full.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lakehouse.redact import find  # noqa: E402

SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".parquet", ".pyc", ".zip", ".gz"}


def git_files(staged_only: bool) -> list[str]:
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"] if staged_only else ["git", "ls-files"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout
    files = [l for l in out.splitlines() if l]
    if not staged_only:
        files += [l for l in subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                                            cwd=ROOT, capture_output=True, text=True).stdout.splitlines() if l]
    return sorted(set(files))


def staged_content(rel: str) -> str | None:
    """The blob as it will be committed (may differ from the working tree)."""
    r = subprocess.run(["git", "show", f":{rel}"], cwd=ROOT, capture_output=True)
    return r.stdout.decode("utf-8", errors="replace") if r.returncode == 0 else None


def iter_paths(args: list[str]) -> list[str]:
    out: list[str] = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            out += [str(q.relative_to(ROOT)) if q.is_relative_to(ROOT) else str(q) for q in p.rglob("*") if q.is_file()]
        else:
            out.append(a)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--staged", action="store_true")
    a = ap.parse_args()

    if a.paths:
        files, use_index = iter_paths(a.paths), False
    else:
        files, use_index = git_files(a.staged), a.staged

    hits = 0
    scanned = 0
    for rel in files:
        if Path(rel).suffix.lower() in SKIP_SUFFIXES:
            continue
        if Path(rel).name in (".env",) or Path(rel).name.endswith(".env"):
            print(f"FORBIDDEN  {rel}: .env files are never committed")
            hits += 1
            continue
        text = staged_content(rel) if use_index else None
        if text is None:
            p = ROOT / rel if not Path(rel).is_absolute() else Path(rel)
            if not p.is_file():
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        scanned += 1
        for lineno, line in enumerate(text.splitlines(), 1):
            for name, masked in find(line):
                print(f"SECRET     {rel}:{lineno}: {name} {masked}")
                hits += 1

    print(f"check-secrets: scanned {scanned} files, {hits} findings → {'FAIL' if hits else 'OK'}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
