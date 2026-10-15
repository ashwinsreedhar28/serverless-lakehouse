{{ config(severity='warn', tags=['runpod']) }}
{#- Every campaign cold start's GPU model needs a row in seeds/campaign_gpu_pins.csv; without one its GPU agreement is
    scored false for both histories instead of being flagged. -#}
select design_gpu_model, count(*) as n_cold_starts
from {{ ref('gold_campaign_config_asof') }}
where expected_gpu_ids is null
group by 1
