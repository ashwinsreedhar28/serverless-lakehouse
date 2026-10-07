{{ config(schema='SILVER') }}
{#- Worker events derived by diffing consecutive polls per endpoint: a worker present now but not in the previous poll
    `appeared` (a scale-up — with FlashBoot off, a cold start), one gone since the previous poll `disappeared` (scaled down),
    and a status change is `status_changed`. Resolution = the poll cadence; a worker that came and went between two polls
    is invisible, which is exactly the limit of snapshot-based observation and why per-job data (silver_runpod_jobs) is the
    other half. -#}
with polls as (select poll_id, poll_seq, polled_at_utc from {{ ref('silver_runpod_polls') }}),
-- every (endpoint, worker) ever seen × every poll in which that endpoint was observed
endpoint_polls as (
    select distinct e.endpoint_id, p.poll_seq, p.poll_id, p.polled_at_utc
    from {{ ref('silver_runpod_endpoints') }} e
    join polls p on p.poll_id = e.poll_id
),
known as (
    select distinct endpoint_id, worker_id from {{ ref('silver_runpod_workers') }}
),
grid as (
    select k.endpoint_id, k.worker_id, ep.poll_seq, ep.poll_id, ep.polled_at_utc,
           w.status, w.gpu_type_id, w.data_center_id, w.started_at_utc, w.uptime_s
    from known k
    join endpoint_polls ep on ep.endpoint_id = k.endpoint_id
    left join {{ ref('silver_runpod_workers') }} w
      on w.endpoint_id = k.endpoint_id and w.worker_id = k.worker_id and w.poll_id = ep.poll_id
),
lagged as (
    select *,
           lag(status)        over (partition by endpoint_id, worker_id order by poll_seq)   as prev_status,
           lag(poll_seq)      over (partition by endpoint_id, worker_id order by poll_seq)   as prev_seq,
           lag(polled_at_utc) over (partition by endpoint_id, worker_id order by poll_seq)   as prev_polled_at_utc
    from grid
),
events as (
    select
        endpoint_id, worker_id, poll_seq, poll_id, polled_at_utc, prev_polled_at_utc,
        case
            when status is not null and prev_status is null and prev_seq is not null   then 'appeared'
            when status is not null and prev_seq is null                                then 'first_seen'
            when status is null and prev_status is not null                             then 'disappeared'
            when status is not null and prev_status is not null and status != prev_status then 'status_changed'
        end                                                                             as event,
        prev_status, status, gpu_type_id, data_center_id, started_at_utc, uptime_s
    from lagged
)
select *, sysdate() as silver_built_at
from events
where event is not null
