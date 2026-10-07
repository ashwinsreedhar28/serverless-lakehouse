{{ config(schema='SILVER') }}
{#- Per-job status look-ups (delayTime / executionTime / workerId) for jobs whose ids the submitter wrote to
    data/runpod/jobs.jsonl; the API keeps a job 30 min after completion, so the latest poll that still saw it wins. -#}
with polls as (select * from {{ ref('silver_runpod_polls') }}),
raw as (
    select b.source_sha256 as poll_id, j.value as job
    from {{ source('bronze', 'bronze_runpod_polls') }} b, lateral flatten(input => b.doc:jobs) j
    qualify row_number() over (partition by b.source_sha256, j.index order by b.ingested_at desc) = 1
),
typed as (
    select
        p.poll_seq, p.polled_at_utc,
        job:endpoint_id::string                                                         as endpoint_id,
        job:job_id::string                                                              as job_id,
        convert_timezone('UTC', job:submitted_at::timestamp_tz)::timestamp_ntz          as submitted_at_utc,
        job:status:status::string                                                       as status,
        job:status:delayTime::number                                                    as delay_ms,
        job:status:executionTime::number                                                as exec_ms,
        job:status:workerId::string                                                     as worker_id,
        job:status:_error::string                                                       as api_error
    from raw r
    join polls p on p.poll_id = r.poll_id
)
select *, sysdate() as silver_built_at
from typed
qualify row_number() over (partition by endpoint_id, job_id order by iff(status in ('COMPLETED', 'FAILED', 'CANCELLED', 'TIMED_OUT'), 1, 0) desc, poll_seq desc) = 1
