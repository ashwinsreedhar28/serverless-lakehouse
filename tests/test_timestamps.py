"""Timestamps leave Spark as explicit UTC strings, whatever the driver's local zone is."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
pytestmark = [pytest.mark.slow, pytest.mark.skipif(shutil.which("java") is None, reason="needs a JVM")]

PROBE = r'''
from datetime import datetime, timezone
from lakehouse.spark import get_spark, timestamps_as_utc_strings
s = get_spark("parquet", "tz-probe")
df = s.createDataFrame([(datetime(2026, 9, 23, 19, 53, 7, tzinfo=timezone.utc),)], "t timestamp")
print("OUT", timestamps_as_utc_strings(df).first()[0], "| naive", df.first()[0].isoformat())
s.stop()
'''


def test_utc_strings_do_not_depend_on_driver_timezone():
    env = {**os.environ, "TZ": "America/New_York", "SPARK_LOCAL_IP": "127.0.0.1"}
    out = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=env, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-2000:]
    line = next(l for l in out.stdout.splitlines() if l.startswith("OUT"))
    assert "2026-09-23T19:53:07Z" in line, line                      # the instant, labelled UTC
    assert "15:53:07" in line                                        # what collect() alone would have shown in US-Eastern
