-- A worker appears at most once per poll per endpoint; a billing bucket once per endpoint.
select poll_id, endpoint_id, worker_id, count(*) as n
from {{ ref('silver_runpod_workers') }} group by 1, 2, 3 having count(*) > 1
union all
select null, endpoint_id, bucket_start_utc::string, count(*)
from {{ ref('silver_runpod_billing_hourly') }} group by 1, 2, 3 having count(*) > 1
