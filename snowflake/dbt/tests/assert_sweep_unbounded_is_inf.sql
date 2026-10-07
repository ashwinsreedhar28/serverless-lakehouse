-- Spark: `request_rate: null` → inf and is_unbounded, nothing else does.
select source_file, run_index, request_rate, is_unbounded
from {{ ref('silver_sweep_summaries') }}
where is_unbounded != (request_rate = 'inf'::double)
union all
select source_file, run_index, request_rate, null
from {{ ref('silver_sweep_requests') }}
where request_rate is null
