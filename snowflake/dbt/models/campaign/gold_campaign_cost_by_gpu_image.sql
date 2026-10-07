{{ config(schema='GOLD', tags=['campaign']) }}
{#- Cold-start cost per GPU × image × FlashBoot: the request-duration proxy from silver beside what Runpod actually billed
    the cell's endpoint (hourly billing records summed over the cell's life) divided by its cold starts. The two differ by
    the idle timeout and the warm request, which is the point of showing both. -#}
with cells as (
    select gpu_model, gpu_tier, flashboot, weights_mode, engine, endpoint_id,
           count(*)                                                 as n_cold_ok,
           sum(iff(coalesce(is_flashboot_hit, false), 1, 0))        as n_hits,
           {{ pct('delay_ms', 0.5) }}                               as delay_ms_p50,
           {{ pct('request_duration_s', 0.5) }}                     as request_duration_s_p50,
           {{ pct('est_cost_usd', 0.5) }}                           as est_cost_usd_p50_proxy,
           min(request_ts_utc)                                      as first_request_utc,
           max(request_ts_utc)                                      as last_request_utc
    from {{ ref('silver_campaign_requests') }}
    where kind = 'cold' and ok and campaign_kind = 'campaign'
    group by 1, 2, 3, 4, 5, 6
),
billed as (
    select c.endpoint_id, round(sum(b.total_usd), 4) as billed_usd
    from cells c
    join {{ ref('silver_runpod_billing_hourly') }} b
      on b.endpoint_id = c.endpoint_id
     and b.bucket_start_utc >= date_trunc('hour', c.first_request_utc)
     and b.bucket_start_utc <= c.last_request_utc
    group by 1
)
select
    c.gpu_model, c.gpu_tier, c.flashboot, c.weights_mode, c.engine, c.endpoint_id,
    c.n_cold_ok, c.n_hits, c.delay_ms_p50, c.request_duration_s_p50, c.est_cost_usd_p50_proxy,
    b.billed_usd,
    round(b.billed_usd / c.n_cold_ok, 4)                            as billed_usd_per_cold,
    c.first_request_utc, c.last_request_utc,
    sysdate()                                                       as gold_built_at
from cells c
left join billed b on b.endpoint_id = c.endpoint_id
order by c.gpu_model, c.weights_mode, c.flashboot
