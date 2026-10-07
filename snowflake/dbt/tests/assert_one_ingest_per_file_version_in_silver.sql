-- Spark: test_force_reingest_does_not_duplicate_silver_events. --force can append the same (file, sha) twice in bronze;
-- silver must carry each natural record once. Worker-log lines are the sharpest check: (file, sha, line_no) is unique.
select source_file, source_sha256, line_no, count(*) as n
from {{ ref('silver_worker_log_events') }}
group by 1, 2, 3
having count(*) > 1
union all
select source_file, source_sha256, run_index, count(*)
from {{ ref('silver_coldstart_requests') }}
where source = 'emberserve_results'
group by source_file, source_sha256, run_index, kind
having count(*) > 1
