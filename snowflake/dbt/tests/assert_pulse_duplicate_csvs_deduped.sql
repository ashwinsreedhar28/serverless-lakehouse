-- Spark: pulse_requests dedupe (results_v0.csv ≡ bench/logs/results_runs1-3.csv, both also in results.csv). The same Pulse
-- request must appear once in silver whichever file it came from.
select endpoint_id, request_ts_utc, kind, run_index, request_index, count(*) as n
from {{ ref('silver_coldstart_requests') }}
where source = 'pulse_coldstart'
group by 1, 2, 3, 4, 5
having count(*) > 1
