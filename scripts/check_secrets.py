#!/usr/bin/env python3
"""Scan files for credentials using the same patterns `lakehouse.land` redacts with.

    scripts/check_secrets.py            # every git-tracked file + anything staged
    scripts/check_secrets.py --staged   # only staged content (what the pre-commit hook runs)
    scripts/check_secrets.py PATH...    # specific files or directories

Exit 1 on any hit. Matches are printed masked, never in full.

Fail-closed rules (an earlier version could be bypassed by each of these):
- paths come from `git ... -z`, split on NUL, so a filename git would quote (non-ASCII, spaces, control chars) is
  still scanned instead of silently dropped;
- a staged blob that cannot be read from the index is a finding, not a skip;
- only true binaries (images, parquet, pyc) are skipped by suffix; a `.pdf`/`.gz`/`.bin` is scanned as bytes
  because a plaintext secret renamed to look binary is the easy way round a suffix list;
- text is decoded as UTF-8, and if that fails or the bytes look like UTF-16, as UTF-16 as well, so a token saved
  from a Windows editor is seen.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lakehouse.redact import find  # noqa: E402

SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".parquet", ".pyc", ".woff", ".woff2", ".ico"}
STAGED_CMD = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]


def _z(cmd: list[str]) -> list[str]:
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, check=True).stdout
    return [p.decode("utf-8", errors="surrogateescape") for p in out.split(b"\0") if p]


def git_files(staged_only: bool) -> list[str]:
    files = _z(STAGED_CMD) if staged_only else _z(["git", "ls-files", "-z"]) + _z(STAGED_CMD)
    return sorted(set(files))


def staged_blob(rel: str) -> bytes | None:
    """The blob as it will be committed (may differ from the working tree); None if git cannot produce it."""
    r = subprocess.run(["git", "show", f":{rel}"], cwd=ROOT, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def decodings(data: bytes) -> list[str]:
    """Every text view worth scanning: UTF-8 (lossy), plus UTF-16 when the bytes carry a BOM or look 16-bit."""
    views = [data.decode("utf-8", errors="replace")]
    looks_utf16 = data[:2] in (b"\xff\xfe", b"\xfe\xff") or (len(data) >= 8 and data[1::2][:64].count(b"\0") > 24)
    if looks_utf16:
        for enc in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                views.append(data.decode(enc))
                break
            except UnicodeDecodeError:
                continue
    return views


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
        name = Path(rel).name
        if Path(rel).suffix.lower() in SKIP_SUFFIXES:
            continue
        if name == ".env" or name.endswith(".env") or name.startswith(".env."):
            print(f"FORBIDDEN  {rel}: .env files are never committed")
            hits += 1
            continue
        data: bytes | None = None
        if use_index:
            data = staged_blob(rel)
            if data is None:
                print(f"UNREADABLE {rel}: staged but `git show :path` failed — refusing to pass what could not be scanned")
                hits += 1
                continue
        else:
            p = ROOT / rel if not Path(rel).is_absolute() else Path(rel)
            if not p.is_file():
                continue
            data = p.read_bytes()
        scanned += 1
        seen: set[tuple[int, str, str]] = set()
        for text in decodings(data):
            for lineno, line in enumerate(text.splitlines(), 1):
                for pname, masked in find(line):
                    if (lineno, pname, masked) in seen:
                        continue
                    seen.add((lineno, pname, masked))
                    print(f"SECRET     {rel}:{lineno}: {pname} {masked}")
                    hits += 1

    print(f"check-secrets: scanned {scanned} files, {hits} findings → {'FAIL' if hits else 'OK'}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
