{{ config(schema='GOLD') }}
{#- One row per endpoint per UTC day: what the polls saw (max active workers, appearances ≈ scale-ups), what the endpoint's
    own counters moved by (jobs completed/failed deltas), and what it cost (billing buckets). -#}
with days as (
    select endpoint_id, polled_at_utc::date as day, count(distinct poll_id) as n_polls,
           max(polled_at_utc) as last_poll_utc
    from {{ ref('silver_runpod_endpoints') }} group by 1, 2
),
cfg as (
    select endpoint_id, polled_at_utc::date as day, name, flashboot, workers_min, workers_max, idle_timeout_s, gpu_pools
    from {{ ref('silver_runpod_endpoints') }}
    qualify row_number() over (partition by endpoint_id, polled_at_utc::date order by poll_seq desc) = 1
),
wk as (
    select endpoint_id, polled_at_utc::date as day,
           count(distinct worker_id) as n_workers_seen,
           max(n_active) as max_active_workers,
           array_sort(array_agg(distinct gpu_type_id)) as gpu_types_seen,
           array_sort(array_agg(distinct data_center_id)) as data_centers_seen
    from (
        select *, count(*) over (partition by poll_id, endpoint_id) as n_active from {{ ref('silver_runpod_workers') }}
    ) group by 1, 2
),
ev as (
    select endpoint_id, polled_at_utc::date as day,
           sum(iff(event = 'appeared', 1, 0)) as n_appeared,
           sum(iff(event = 'disappeared', 1, 0)) as n_disappeared,
           sum(iff(event = 'status_changed', 1, 0)) as n_status_changes
    from {{ ref('silver_runpod_worker_events') }} group by 1, 2
),
hl as (
    select endpoint_id, polled_at_utc::date as day,
           max(jobs_completed) - min(jobs_completed) as jobs_completed_delta,
           max(jobs_failed) - min(jobs_failed) as jobs_failed_delta,
           max(jobs_retried) - min(jobs_retried) as jobs_retried_delta,
           max(workers_running + workers_idle + workers_ready) as max_workers_by_health
    from {{ ref('silver_runpod_health') }} group by 1, 2
),
bl as (
    select endpoint_id, bucket_start_utc::date as day,
           round(sum(total_usd), 4) as total_usd, round(sum(gpu_usd), 4) as gpu_usd, count(*) as n_billing_hours
    from {{ ref('silver_runpod_billing_hourly') }} group by 1, 2
)
select
    d.endpoint_id, d.day, c.name, c.flashboot, c.workers_min, c.workers_max, c.idle_timeout_s, c.gpu_pools,
    d.n_polls, d.last_poll_utc,
    coalesce(w.n_workers_seen, 0) as n_workers_seen, coalesce(w.max_active_workers, 0) as max_active_workers,
    w.gpu_types_seen, w.data_centers_seen,
    coalesce(e.n_appeared, 0) as n_worker_appearances, coalesce(e.n_disappeared, 0) as n_worker_disappearances,
    coalesce(e.n_status_changes, 0) as n_status_changes,
    h.jobs_completed_delta, h.jobs_failed_delta, h.jobs_retried_delta, h.max_workers_by_health,
    b.total_usd, b.gpu_usd, b.n_billing_hours,
    sysdate() as gold_built_at
from days d
left join cfg c on c.endpoint_id = d.endpoint_id and c.day = d.day
left join wk w on w.endpoint_id = d.endpoint_id and w.day = d.day
left join ev e on e.endpoint_id = d.endpoint_id and e.day = d.day
left join hl h on h.endpoint_id = d.endpoint_id and h.day = d.day
left join bl b on b.endpoint_id = d.endpoint_id and b.day = d.day
order by d.endpoint_id, d.day
