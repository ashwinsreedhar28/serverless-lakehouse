"""End-to-end scenarios the first external audit reproduced: silver must follow the landing manifest, not
bronze's newest timestamp; the ingest ledger must self-repair. Runs the real CLIs against a throw-away landing
and lakehouse (parquet, so no Delta jars needed) — slow (~2 min), needs Java.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
pytestmark = [pytest.mark.slow, pytest.mark.skipif(shutil.which("java") is None, reason="needs a JVM")]


def coldstart(label: str, n_runs: int) -> str:
    runs = [{"health_before": {"workers": {"idle": 1}},
             "cold": {"status": 200, "total_s": 20.0 + i, "ok": True, "job_status": "COMPLETED", "delay_ms": 19000 + i, "execution_ms": 900, "worker_id": f"w{i}"},
             "warm": {"status": 200, "total_s": 0.5, "ok": True, "job_status": "COMPLETED", "delay_ms": 20, "execution_ms": 400, "worker_id": f"w{i}"}}
            for i in range(n_runs)]
    return json.dumps({"kind": "serverless_coldstart", "mode": "queue", "endpoint": "ep1", "label": label, "image": "test",
                       "note": "", "max_tokens": 16, "idle_s": 60.0, "runs": runs, "summary": {"failures": 0}})


def sweep(with_records: bool) -> str:
    run = {"request_rate": 1.0, "wall_s": 10.0, "summary": {"num_requests": 2, "completed": 2, "failed": 0}, "trace": {"n": 2}}
    if with_records:
        run["records"] = [{"request_id": f"req-{i}", "arrival_s": 1.0 + i, "first_token_s": 1.5 + i, "finish_s": 2.0 + i,
                           "prompt_tokens": 10, "output_tokens": 5, "success": True, "error": None} for i in range(2)]
    return json.dumps({"kind": "sweep", "system": "sys", "server": "vllm", "base_url": "https://api.runpod.ai/v2/ep1/openai/v1",
                       "model": "m", "args": {"api_key": "<redacted>"}, "runs": [run]})


class Pipeline:
    def __init__(self, tmp: Path):
        self.src = tmp / "src"
        (self.src / "emberserve" / "results").mkdir(parents=True)
        (self.src / "pulse").mkdir()
        self.env = {**os.environ, "LANDING_DIR": str(tmp / "landing"), "LAKEHOUSE_DIR": str(tmp / "lakehouse"),
                    "SPARK_LOCAL_IP": "127.0.0.1"}
        self.results = self.src / "emberserve" / "results"

    def run(self, *mod: str) -> str:
        out = subprocess.run([sys.executable, "-m", f"lakehouse.{mod[0]}", *mod[1:]], cwd=ROOT, env=self.env,
                             capture_output=True, text=True)
        assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-3000:]
        return out.stdout

    def land(self):
        return self.run("land", "--emberserve", str(self.src / "emberserve"), "--pulse", str(self.src / "pulse"),
                        "--landing-dir", self.env["LANDING_DIR"])

    def bronze(self, label: str):
        return self.run("bronze", "--run-label", label, "--format", "parquet", "--landing-dir", self.env["LANDING_DIR"])

    def silver(self):
        return self.run("silver", "--format", "parquet")

    def count(self, table: str, **where) -> int:
        """Count rows in a parquet table without starting a JVM."""
        import glob
        import pyarrow.parquet as pq
        files = glob.glob(str(Path(self.env["LAKEHOUSE_DIR"]) / "silver" / table / "*.parquet")) or \
                glob.glob(str(Path(self.env["LAKEHOUSE_DIR"]) / "bronze" / table / "*.parquet"))
        n = 0
        for f in files:
            t = pq.read_table(f).to_pylist()
            n += sum(1 for r in t if all(r.get(k) == v for k, v in where.items()))
        return n


@pytest.fixture(scope="module")
def pipe(tmp_path_factory):
    pytest.importorskip("pyarrow")
    return Pipeline(tmp_path_factory.mktemp("lh"))


def test_revert_rename_and_empty_records_follow_the_manifest(pipe: Pipeline):
    A, B = coldstart("series_a", 2), coldstart("series_a", 1)
    f = pipe.results / "serverless_coldstart_a.json"
    f.write_text(A); pipe.land(); pipe.bronze("r1"); pipe.silver()
    assert pipe.count("silver_coldstart_requests") == 4                 # 2 runs × cold+warm

    f.write_text(B); pipe.land(); pipe.bronze("r2"); pipe.silver()
    assert pipe.count("silver_coldstart_requests") == 2                 # replacement selected

    f.write_text(A); pipe.land()
    out = pipe.bronze("r3")
    assert "nothing new" in out                                         # (path, sha) of A already in bronze
    pipe.silver()
    assert pipe.count("silver_coldstart_requests") == 4                 # reverted file selected again, not "newest"

    f.rename(pipe.results / "serverless_coldstart_renamed.json"); pipe.land(); pipe.bronze("r4"); pipe.silver()
    assert pipe.count("silver_coldstart_requests") == 4
    assert pipe.count("silver_coldstart_requests", source_file="emberserve/results/serverless_coldstart_a.json") == 0

    sw = pipe.results / "runpod_serverless_s.json"
    sw.write_text(sweep(True)); pipe.land(); pipe.bronze("r5"); pipe.silver()
    assert pipe.count("silver_sweep_requests") == 2
    sw.write_text(sweep(False)); pipe.land(); pipe.bronze("r6"); pipe.silver()
    assert pipe.count("silver_sweep_requests") == 0                     # no records in the current version → none in silver
    assert pipe.count("silver_sweep_summaries") == 1


def test_interrupted_run_repairs_the_ingest_log(pipe: Pipeline):
    log_dir = Path(pipe.env["LAKEHOUSE_DIR"]) / "bronze" / "bronze_ingest_log"
    shutil.rmtree(log_dir)                                              # data tables written, ledger lost
    out = pipe.bronze("r7")
    assert "repaired" in out, out
    assert pipe.count("bronze_ingest_log", reconciled=True) > 0


def test_silver_refuses_when_bronze_lacks_the_current_version(pipe: Pipeline):
    (pipe.results / "serverless_coldstart_new.json").write_text(coldstart("series_new", 1)); pipe.land()
    r = subprocess.run([sys.executable, "-m", "lakehouse.silver", "--format", "parquet"], cwd=ROOT, env=pipe.env,
                       capture_output=True, text=True)
    assert r.returncode != 0 and "not in bronze" in (r.stdout + r.stderr)
