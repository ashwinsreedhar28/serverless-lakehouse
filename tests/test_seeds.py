"""Seeds are hand-written CSVs; a stray comma shifts every column after it. Check shape and enumerations."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "seeds"


def rows(name):
    with (ROOT / name).open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        out = list(r)
        assert all(None not in row and None not in row.values() for row in out), f"{name}: ragged row (unquoted comma?)"
        return r.fieldnames, out


def test_coldstart_series():
    cols, data = rows("coldstart_series.csv")
    assert cols == ["series_label", "engine", "engine_build", "model", "gpu_model", "flashboot", "flashboot_source",
                    "weights_mode", "image_gb", "notes"]
    assert len(data) == 13 and len({r["series_label"] for r in data}) == 13
    for r in data:
        assert r["engine"] in ("emberserve", "worker-vllm"), r
        assert r["flashboot"] in ("on", "off", "unknown"), r
        assert r["weights_mode"] in ("baked", "fetched"), r
        assert r["flashboot_source"], r


def test_gpu_labels():
    cols, data = rows("gpu_labels.csv")
    assert cols == ["gpu_label", "tier", "gpu_model", "price_per_hr_usd", "evidence", "source", "notes"]
    assert len({r["gpu_label"] for r in data}) == len(data)
    for r in data:
        assert r["evidence"] in ("observed", "inferred", "unknown"), r
        assert r["source"], r
        if r["price_per_hr_usd"]:
            float(r["price_per_hr_usd"])
        if r["evidence"] == "unknown":
            assert r["gpu_model"] == "", r      # unknown means unknown, not a guess


def test_run_notes():
    cols, data = rows("coldstart_run_notes.csv")
    assert cols == ["series_label", "run_index", "host_state", "evidence", "note", "source"]
    for r in data:
        int(r["run_index"])
        assert r["host_state"] in ("fresh_host", "warm_host", "partial_host", "flashboot_resume"), r
        assert r["evidence"] and r["source"], r
    assert len({(r["series_label"], r["run_index"]) for r in data}) == len(data)


def test_evidence_file_present():
    assert (ROOT / "evidence" / "gpu_per_cycle.txt").is_file()
