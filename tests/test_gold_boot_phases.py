"""Boot segmentation in gold_worker_boot_phases, on a synthetic silver_worker_log_events frame.

The fourth audit found the previous rule ("a boot opens at `Starting vLLM:`") merged two boots that shared one
wrapper line into a chimera row and dropped boots with no wrapper line at all. Starts a JVM, so marked slow.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone

import pytest

pytestmark = [pytest.mark.slow, pytest.mark.skipif(shutil.which("java") is None, reason="needs a JVM")]


def ts(minute: int, second: int = 0):
    return datetime(2026, 9, 23, 18, minute, second, tzinfo=timezone.utc).replace(tzinfo=None)


def ev(spark, rows):
    """rows: (source_file, worker_id, line_no, minute, second, message)."""
    from pyspark.sql import types as T
    schema = T.StructType([T.StructField("source_file", T.StringType()), T.StructField("worker_id", T.StringType()),
                           T.StructField("line_no", T.IntegerType()), T.StructField("ts_utc", T.TimestampType()),
                           T.StructField("ts_format", T.StringType()), T.StructField("event_kind", T.StringType()),
                           T.StructField("message", T.StringType())])
    return spark.createDataFrame([(f, w, n, ts(m, s), "pipe", "vllm", msg) for f, w, n, m, s, msg in rows], schema)


BOOT_LINES = [  # one complete boot, offsets in seconds from its first line
    (0, "Starting vLLM: vllm serve --host 127.0.0.1"),
    (45, "Initializing a V1 LLM engine (v0.28.0) with config: model='qwen/qwen3-8b'"),
    (90, "Loading weights took 18.12 seconds"),
    (150, "Graph capturing finished in 6 secs, took 0.58 GiB"),
    (160, "Graph capturing finished in 7 secs, took 0.58 GiB"),
    (165, "init engine (profile, create kv cache, warmup model) took 56.34 s (compilation: 37.27 s)"),
    (170, "Application startup complete."),
]


def boot(file, worker, line0, minute0, lines=BOOT_LINES, skip_start=False):
    out = []
    for i, (off, msg) in enumerate(lines):
        if skip_start and msg.startswith("Starting vLLM:"):
            continue
        out.append((file, worker, line0 + i, minute0 + off // 60, off % 60, msg))
    return out


@pytest.fixture(scope="module")
def spark():
    from lakehouse.spark import get_spark
    s = get_spark("parquet", app="test-boot-phases")
    yield s
    s.stop()


def test_segmentation_opens_boots_at_wrapper_or_orphan_init_and_keeps_headless_boots(spark):
    from lakehouse.gold import worker_boot_phases
    rows = (
        boot("a.log", "w1", 1, 0)                                   # ordinary boot: wrapper + init
        + boot("a.log", "w1", 100, 10, skip_start=True)             # same worker, console missed the wrapper line → orphan init
        + boot("a.log", "w2", 200, 20, skip_start=True)             # another worker interleaved, no wrapper line at all
        + boot("b.log", None, 1, 30, lines=BOOT_LINES[2:])          # log starts mid-boot: no wrapper, no init
        + boot("c.log", None, 1, 40) + boot("c.log", None, 50, 50)  # two clean restarts in one log
    )
    out = {(r.source_file, r.worker_id or "", r.boot_index): r for r in worker_boot_phases(ev(spark, rows)).collect()}
    assert len(out) == 6, sorted(out)

    a1, a2, a_w2 = out[("a.log", "w1", 1)], out[("a.log", "w1", 2)], out[("a.log", "w2", 1)]
    assert a1.segmented_by.startswith("Starting vLLM") and a1.start_to_api_ready_s == 170.0
    assert a2.segmented_by.startswith("Initializing") and a2.t_start_vllm is None and a2.start_to_api_ready_s is None
    assert a_w2.segmented_by.startswith("Initializing") and a_w2.weights_load_s == 18.12       # the dropped boot is back
    assert a1.init_engine_s == a2.init_engine_s == 56.34                                       # no borrowing between boots

    b0 = out[("b.log", "", 0)]
    assert b0.segmented_by.startswith("none") and b0.torch_compile_s is None and b0.init_engine_s == 56.34

    assert {k[2] for k in out if k[0] == "c.log"} == {1, 2}
    # graph capture is the sum of the passes, and the pass count is kept
    assert all(r.graph_capture_s == 13.0 and r.n_graph_passes == 2 for r in out.values())


def test_lines_before_the_first_boot_without_phases_are_not_a_boot(spark):
    from lakehouse.gold import worker_boot_phases
    rows = [("d.log", None, 1, 0, 0, "Registered model loader"), ("d.log", None, 2, 0, 1, "world_size=1 rank=0")] \
        + boot("d.log", None, 3, 1)
    out = worker_boot_phases(ev(spark, rows)).collect()
    assert [r.boot_index for r in out] == [1]
