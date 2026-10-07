{{ config(schema='GOLD', tags=['campaign']) }}
{#- FlashBoot hit rate vs idle gap: for cold-labelled requests, the gap since the previous request on the same endpoint,
    bucketed, against the share answered under the hit threshold. With FlashBoot off the rate should be ~0 in every bucket;
    with it on, the bucket where the rate drops is how long Runpod keeps a worker resumable. -#}
with cold as (
    select *,
        case when gap_since_prev_request_s is null then 'first'
             when gap_since_prev_request_s < 120 then '<2 min'
             when gap_since_prev_request_s < 600 then '2-10 min'
             when gap_since_prev_request_s < 3600 then '10-60 min'
             else '>60 min' end as gap_bucket
    from {{ ref('silver_campaign_requests') }}
    where kind = 'cold' and ok
)
select
    gpu_model, flashboot, weights_mode, engine, campaign_kind, gap_bucket,
    count(*)                                                        as n_cold,
    sum({{ b2i('coalesce(is_flashboot_hit, false)') }})            as n_hits,
    round(n_hits::double / n_cold, 3)                               as hit_rate,
    {{ pct('iff(coalesce(is_flashboot_hit, false), delay_ms, null)', 0.5) }}       as hit_delay_ms_p50,
    {{ pct('iff(not coalesce(is_flashboot_hit, false), delay_ms, null)', 0.5) }}   as miss_delay_ms_p50,
    {{ pct('gap_since_prev_request_s', 0.5) }}                      as gap_s_p50,
    sysdate()                                                       as gold_built_at
from cold
group by 1, 2, 3, 4, 5, 6
order by gpu_model, flashboot, weights_mode, gap_bucket
