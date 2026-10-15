{{ config(schema='GOLD') }}
{#- How often each config history puts a campaign cold start on the config its cell actually ran with. One row per
    history × attribute. Chance level is 25 % for GPU (four GPU models) and 50 % for FlashBoot (on/off). -#}
with a as (select * from {{ ref('gold_campaign_config_asof') }}),
u as (
    select 'release log (timestamp strategy)' as history, 'gpu' as attribute,
           count(*) as n_cold_starts, count_if(release_gpu_agrees) as n_agree from a
    union all
    select 'polls (check strategy)', 'gpu', count(*), count_if(poll_gpu_agrees) from a
    union all
    select 'polls (check strategy)', 'flashboot', count(*), count_if(poll_flashboot_agrees) from a
)
select history, attribute, n_cold_starts, n_agree, round(100.0 * n_agree / nullif(n_cold_starts, 0), 1) as pct_agree,
       sysdate() as gold_built_at
from u
