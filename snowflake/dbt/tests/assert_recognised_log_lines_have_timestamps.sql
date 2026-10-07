-- Spark: silver prints "worker-log lines without a parsed timestamp"; here a line whose format was recognised but whose
-- timestamp did not parse to UTC is a failure (a format regex and its TO_TIMESTAMP mask drifting apart).
select source_file, line_no, ts_format, raw_line_prefix
from (
    select source_file, line_no, ts_format, left(payload, 60) as raw_line_prefix, ts_utc
    from {{ ref('silver_worker_log_events') }}
)
where ts_format != 'none' and ts_utc is null
