{#- Estimated $ per Serverless request, per engine × model × GPU × weights mode × kind. Port of lakehouse.gold.cost_per_job. -#}

with priced as (
    select * from {{ ref('silver_coldstart_requests') }}
    where ok and price_per_hr_usd is not null
)

select
    engine, model,
    coalesce(gpu_model, 'not captured')                             as gpu_model,
    gpu_tier, weights_mode, kind, price_per_hr_usd,
    count(*)                                                        as n,
    {{ pct('request_duration_s', 0.5) }}                            as request_duration_s_p50,
    {{ pct('request_duration_s', 0.9) }}                            as request_duration_s_p90,
    {{ pct('est_cost_usd', 0.5) }}                                  as est_cost_usd_p50,
    round(sum(est_cost_usd), 4)                                     as est_cost_usd_total,
    'request-duration proxy: (delay_ms + exec_ms) / 3.6e6 * price_per_hr_usd; not billed time (Runpod bills worker start + execution + idle per worker)'   as cost_formula,
    sysdate()                                                       as gold_built_at
from priced
group by engine, model, gpu_model, gpu_tier, weights_mode, kind, price_per_hr_usd
order by engine, model, kind, gpu_tier
