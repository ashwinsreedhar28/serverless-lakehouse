-- Spark: tests/test_timestamps.py — the console-format line "Wed Sep 23 2026 15:53:07 GMT-0400" is the instant
-- 2026-09-23T19:53:07Z. Any console or pipe line in the data whose parsed UTC time equals its wall-clock text was not
-- converted (the laptop-local time was stored as if it were UTC).
select e.source_file, e.line_no, e.ts_format, e.ts_utc, left(e.payload, 40) as payload_prefix
from {{ ref('silver_worker_log_events') }} e
join {{ source('bronze', 'bronze_worker_log_lines') }} b
  on b.source_file = e.source_file and b.source_sha256 = e.source_sha256 and b.line_no = e.line_no
where e.ts_format = 'pipe'
  and to_char(e.ts_utc, 'YYYY-MM-DD HH24:MI:SS.FF3') = left(b.raw_line, 23)
