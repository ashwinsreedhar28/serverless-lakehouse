{{ config(schema='GOLD', tags=['campaign']) }}
{#- Cold-start cost per GPU × image × FlashBoot (one row per cell): the request-duration proxy from silver, and beside it what
    Runpod billed the cell's endpoint in the hours the cell ran. Cells share an endpoint per image (the build endpoint is
    re-pointed per cell), so an hourly bucket can hold more than one cell; billed_usd_endpoint_hours is that shared figure,
    not a per-cell number — the proxy is per cell, the bill is per endpoint-hour, and the gap between them is the idle
    timeout, the warm request and the sharing. -#}
with cells as (
    select series_label, gpu_model, gpu_tier, flashboot, weights_mode, engine, endpoint_id,
           count(*)                                                 as n_cold_ok,
           sum(iff(coalesce(is_flashboot_hit, false), 1, 0))        as n_hits,
           {{ pct('delay_ms', 0.5) }}                               as delay_ms_p50,
           {{ pct('request_duration_s', 0.5) }}                     as request_duration_s_p50,
           {{ pct('est_cost_usd', 0.5) }}                           as est_cost_usd_p50_proxy,
           round(sum(est_cost_usd), 4)                              as est_cost_usd_total_proxy,
           min(request_ts_utc)                                      as first_request_utc,
           max(request_ts_utc)                                      as last_request_utc
    from {{ ref('silver_campaign_requests') }}
    where kind = 'cold' and ok and campaign_kind = 'campaign'
    group by 1, 2, 3, 4, 5, 6, 7
),
hours as (
    select distinct c.series_label, b.endpoint_id, b.bucket_start_utc, b.total_usd
    from cells c
    join {{ ref('silver_campaign_requests') }} r on r.series_label = c.series_label and r.ok
    join {{ ref('silver_runpod_billing_hourly') }} b
      on b.endpoint_id = c.endpoint_id and b.bucket_start_utc = date_trunc('hour', r.request_ts_utc)
),
billed as (
    select series_label, round(sum(total_usd), 4) as billed_usd_endpoint_hours, count(*) as n_billed_hours
    from hours group by 1
)
select
    c.series_label as cell, c.gpu_model, c.gpu_tier, c.flashboot, c.weights_mode, c.engine, c.endpoint_id,
    c.n_cold_ok, c.n_hits, c.delay_ms_p50, c.request_duration_s_p50, c.est_cost_usd_p50_proxy, c.est_cost_usd_total_proxy,
    b.billed_usd_endpoint_hours, b.n_billed_hours,
    c.first_request_utc, c.last_request_utc,
    sysdate()                                                       as gold_built_at
from cells c
left join billed b on b.series_label = c.series_label
order by c.gpu_model, c.weights_mode, c.flashboot
