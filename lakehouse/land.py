"""Landing step (the *extract*): copy the benchmark artefacts from their source checkouts into
data/landing/, redacting credentials on the way, and write a manifest with a sha256 per file.

    python -m lakehouse.land --emberserve ~/emberserve --pulse ~/Pulse

Rules
- Only the file patterns listed in SOURCES are picked up; anything else in those trees is ignored,
  and `.env`-style files are refused even if a pattern would match them.
- Landing is a *mirror* of the sources, not a history: re-running overwrites files and rewrites the
  manifest. History lives in bronze, which is append-only and keyed by the sha256 recorded here.
- The manifest records sha256 of both the original bytes (provenance) and the landed bytes (what
  bronze will actually read). They differ only when something was redacted.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .config import LANDING_DIR, MANIFEST_PATH
from .redact import redact

# (source_root_key, glob relative to that root, dataset tag, exclude globs on the file name)
SOURCES: list[tuple[str, str, str, tuple[str, ...]]] = [
    # emberserve (formerly pagedserve; file names inside still carry the old name):
    # Runpod Serverless cold-start series and load sweeps
    ("emberserve", "results/serverless_coldstart_*.json",          "coldstart_series",       ()),
    ("emberserve", "results/serverless_coldstart_*_worker_log.txt", "worker_log",             ()),
    ("emberserve", "results/runpod_serverless_*.json",             "sweep",                  ()),
    # Pulse: coldstart.py / throughput.py / quality.py outputs
    ("pulse", "results.csv",                   "pulse_coldstart",        ()),
    ("pulse", "results_v0.csv",                "pulse_coldstart",        ()),
    ("pulse", "bench/logs/results_runs1-3.csv", "pulse_coldstart",       ()),
    ("pulse", "results_throughput.csv",        "pulse_throughput",       ()),
    ("pulse", "bench/quality.csv",             "pulse_quality",          ()),
    ("pulse", "bench/quality_batches.csv",     "pulse_quality_batches",  ()),
    # worker logs copied from the Runpod console / API; quality_*.log is quality.py stdout, not a worker log
    ("pulse", "bench/logs/*.log",              "worker_log",             ("quality_*.log",)),
]

# Never landed, whatever the glob says.
FORBIDDEN_NAMES = (".env", "*.env", ".env.*", "*.pem", "*.key", ".DS_Store")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def is_forbidden(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in FORBIDDEN_NAMES)


def discover(roots: dict[str, Path]) -> list[tuple[str, str, Path, str]]:
    """Return [(root_key, source_relpath, abs_path, dataset)] for every file matched by SOURCES."""
    found: list[tuple[str, str, Path, str]] = []
    seen: set[Path] = set()
    for root_key, pattern, dataset, excludes in SOURCES:
        root = roots[root_key]
        for p in sorted(root.glob(pattern)):
            if not p.is_file() or p in seen:
                continue
            if is_forbidden(p.name) or any(fnmatch.fnmatch(p.name, ex) for ex in excludes):
                continue
            seen.add(p)
            found.append((root_key, p.relative_to(root).as_posix(), p, dataset))
    return found


def land_file(root_key: str, relpath: str, src: Path, dataset: str, landing_dir: Path) -> dict:
    raw = src.read_bytes()
    text = raw.decode("utf-8")  # every source is UTF-8 text (json/csv/log); a binary here is a bug
    redacted, hits = redact(text)
    out = landing_dir / root_key / relpath
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(redacted, encoding="utf-8", newline="")  # newline="" keeps the source's line endings
    landed = out.read_bytes()
    return {
        "dataset": dataset,
        "source_root": root_key,
        "source_relpath": relpath,
        "landed_relpath": out.relative_to(landing_dir).as_posix(),
        "bytes_source": len(raw),
        "bytes_landed": len(landed),
        "sha256_source": sha256_bytes(raw),
        "sha256_landed": sha256_bytes(landed),
        "lines": text.count("\n") + (0 if text.endswith("\n") or not text else 1),
        "source_mtime_utc": datetime.fromtimestamp(src.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
        "redactions": dict(hits),
    }


def resolve_emberserve(given: Path | None) -> Path:
    """The inference-engine repo is being renamed pagedserve → emberserve; accept either local name."""
    if given is not None:
        return given.expanduser()
    for cand in (Path("~/emberserve"), Path("~/pagedserve")):
        if cand.expanduser().is_dir():
            return cand.expanduser()
    return Path("~/emberserve").expanduser()


def tilde(p: Path) -> str:
    """Store source roots with $HOME collapsed to ~ so the manifest is the same on every machine."""
    home = Path.home()
    try:
        return "~/" + p.expanduser().absolute().relative_to(home).as_posix()
    except ValueError:
        return str(p)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--emberserve", type=Path, default=None,
                    help="emberserve checkout (default ~/emberserve, falling back to ~/pagedserve while the rename lands)")
    ap.add_argument("--pulse", type=Path, default=Path("~/Pulse").expanduser())
    ap.add_argument("--landing-dir", type=Path, default=LANDING_DIR)
    args = ap.parse_args(argv)

    roots = {"emberserve": resolve_emberserve(args.emberserve), "pulse": args.pulse.expanduser()}
    for k, r in roots.items():
        if not r.is_dir():
            print(f"land: source root for {k!r} not found: {r}", file=sys.stderr)
            return 2

    files = discover(roots)
    if not files:
        print("land: no source files matched", file=sys.stderr)
        return 2

    landing_dir: Path = args.landing_dir
    landing_dir.mkdir(parents=True, exist_ok=True)
    entries = [land_file(*f, landing_dir) for f in files]

    manifest = {
        "landed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool": f"lakehouse.land {__version__}",
        "source_roots": {k: tilde(v) for k, v in roots.items()},
        "n_files": len(entries),
        "bytes_landed": sum(e["bytes_landed"] for e in entries),
        "redactions_total": sum(sum(e["redactions"].values()) for e in entries),
        "files": entries,
    }
    manifest_path = landing_dir / MANIFEST_PATH.name
    manifest_path.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")

    by_ds: dict[str, int] = {}
    for e in entries:
        by_ds[e["dataset"]] = by_ds.get(e["dataset"], 0) + 1
    print(f"landed {len(entries)} files, {manifest['bytes_landed']:,} bytes → {landing_dir}")
    for ds, n in sorted(by_ds.items()):
        print(f"  {ds:<24} {n:>3} files")
    print(f"  redactions: {manifest['redactions_total']}")
    for e in entries:
        if e["redactions"]:
            print(f"    {e['landed_relpath']}: {e['redactions']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
