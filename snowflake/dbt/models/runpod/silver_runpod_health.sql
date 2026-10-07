{{ config(schema='SILVER') }}
{#- The endpoint's own counters per poll: jobs completed / failed / in progress / in queue / retried, and worker counts
    by state. Deltas between polls are the only job-throughput signal the API gives without job ids. -#}
with polls as (select * from {{ ref('silver_runpod_polls') }}),
raw as (
    select b.source_sha256 as poll_id, h.key as endpoint_id, h.value as resp
    from {{ source('bronze', 'bronze_runpod_polls') }} b, lateral flatten(input => b.doc:health) h
    qualify row_number() over (partition by b.source_sha256, h.key order by b.ingested_at desc) = 1
)
select
    p.poll_id, p.poll_seq, p.polled_at_utc, r.endpoint_id,
    resp:jobs:completed::number         as jobs_completed,
    resp:jobs:failed::number            as jobs_failed,
    resp:jobs:inProgress::number        as jobs_in_progress,
    resp:jobs:inQueue::number           as jobs_in_queue,
    resp:jobs:retried::number           as jobs_retried,
    resp:workers:idle::number           as workers_idle,
    resp:workers:initializing::number   as workers_initializing,
    resp:workers:ready::number          as workers_ready,
    resp:workers:running::number        as workers_running,
    resp:workers:throttled::number      as workers_throttled,
    resp:workers:unhealthy::number      as workers_unhealthy,
    resp:_error::string                 as api_error,
    sysdate()                           as silver_built_at
from raw r
join polls p on p.poll_id = r.poll_id
