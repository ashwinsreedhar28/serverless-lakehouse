{{ config(severity='warn', tags=['runpod']) }}
{#- The campaign pins each GPU model with one pool + exclusion list (tools/campaign.py resolve_gpu). If the release
    history is right, every cold start of a GPU model lands on that one pin; more than one means the as-of join or the
    release rebuild put some cold starts on the wrong version. -#}
select design_gpu_model, any_value(n_pins) as n_pins, array_agg(distinct release_gpu_ids) as pins_seen
from {{ ref('gold_campaign_config_asof') }}
group by 1
having any_value(n_pins) <> 1 or count_if(release_gpu_ids is null) > 0
