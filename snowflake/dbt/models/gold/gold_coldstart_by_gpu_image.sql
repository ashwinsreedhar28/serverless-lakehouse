{#- Cold-start distribution per engine × model × GPU × weights mode × FlashBoot × kind. Port of lakehouse.gold.coldstart_by_gpu_image. -#}

with ok as (
    select * from {{ ref('silver_coldstart_requests') }} where ok
)

select
    engine, model,
    coalesce(gpu_model, 'not captured')                                 as gpu_model,
    gpu_tier, weights_mode, flashboot, kind,
    count(*)                                                            as n,
    sum({{ b2i('is_flashboot_hit') }})                                  as n_flashboot_hits,
    {{ pct('delay_ms', 0.5) }}                                          as delay_ms_p50,
    {{ pct('delay_ms', 0.9) }}                                          as delay_ms_p90,
    min(delay_ms)                                                       as delay_ms_min,
    max(delay_ms)                                                       as delay_ms_max,
    {{ pct('exec_ms', 0.5) }}                                           as exec_ms_p50,
    {{ pct('iff(not coalesce(is_flashboot_hit, false), delay_ms, null)', 0.5) }}   as full_boot_delay_ms_p50,
    {{ pct('est_cost_usd', 0.5) }}                                      as est_cost_usd_p50,
    count(distinct endpoint_id)                                         as n_endpoints,
    count(distinct worker_id)                                           as n_workers_seen,
    sysdate()                                                           as gold_built_at
from ok
group by engine, model, gpu_model, gpu_tier, weights_mode, flashboot, kind
order by engine, model, gpu_model, weights_mode, flashboot, kind
