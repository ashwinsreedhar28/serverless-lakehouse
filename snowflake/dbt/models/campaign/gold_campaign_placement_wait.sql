{{ config(schema='GOLD', tags=['campaign']) }}
{#- Placement wait vs availability tier: per GPU tier × FlashBoot × image × UTC slot, how long a cold request waited
    (Runpod delayTime = queue + worker start) and, for emberserve cells with --timeline, the part of it that was placement +
    image pull + container create, which is the tier's availability as the scheduler experienced it. -#}
select
    gpu_tier, gpu_model, flashboot, weights_mode, engine, slot_utc,
    sum(iff(ok, 1, 0))                                              as n_cold_ok,
    sum(iff(not ok, 1, 0))                                          as n_failed,
    {{ pct('delay_ms', 0.5) }}                                      as delay_ms_p50,
    min(delay_ms)                                                   as delay_ms_min,
    max(delay_ms)                                                   as delay_ms_max,
    {{ pct('placement_pull_create_s', 0.5) }}                       as placement_pull_create_s_p50,
    max(placement_pull_create_s)                                    as placement_pull_create_s_max,
    {{ pct('engine_boot_s', 0.5) }}                                 as engine_boot_s_p50,
    count(distinct endpoint_id)                                     as n_endpoints,
    count(distinct worker_id)                                       as n_workers_seen,
    sysdate()                                                       as gold_built_at
from {{ ref('silver_campaign_requests') }}
where kind = 'cold' and campaign_kind = 'campaign'
group by 1, 2, 3, 4, 5, 6
order by gpu_tier, flashboot, weights_mode, slot_utc
