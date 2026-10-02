"""The committed landing zone must agree with its manifest, contain no secrets, and hold only
the file types bronze knows how to read."""

import hashlib
import json
from pathlib import Path

import pytest

from lakehouse.bronze import CSV_TABLE_BY_DATASET, READERS
from lakehouse.config import LANDING_DIR, MANIFEST_PATH
from lakehouse.land import FORBIDDEN_NAMES, is_forbidden
from lakehouse.redact import find

pytestmark = pytest.mark.skipif(not MANIFEST_PATH.is_file(), reason="no landing zone; run `make land`")


def manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_every_manifest_entry_matches_its_file():
    m = manifest()
    assert m["n_files"] == len(m["files"]) > 0
    for e in m["files"]:
        p = LANDING_DIR / e["landed_relpath"]
        assert p.is_file(), e["landed_relpath"]
        b = p.read_bytes()
        assert len(b) == e["bytes_landed"]
        assert hashlib.sha256(b).hexdigest() == e["sha256_landed"]


def test_every_landed_file_is_in_the_manifest():
    listed = {e["landed_relpath"] for e in manifest()["files"]}
    on_disk = {p.relative_to(LANDING_DIR).as_posix() for p in LANDING_DIR.rglob("*") if p.is_file()} - {MANIFEST_PATH.name}
    assert on_disk == listed


def test_every_dataset_has_a_reader():
    for e in manifest()["files"]:
        assert e["dataset"] in READERS or e["dataset"] in CSV_TABLE_BY_DATASET, e["dataset"]


def test_no_forbidden_names_and_no_secrets():
    for p in LANDING_DIR.rglob("*"):
        if p.is_file():
            assert not is_forbidden(p.name), p
            for lineno, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                assert find(line) == [], f"{p}:{lineno}"


def test_forbidden_patterns_cover_env_files():
    for name in (".env", "prod.env", ".env.local", "id_rsa.key", "cert.pem"):
        assert is_forbidden(name), name
    assert ".env" in FORBIDDEN_NAMES
