{{ config(schema='GOLD') }}
{#- The benchmark's FlashBoot setting per endpoint (seeds: what the series label said, or "unknown") beside what the API
    says the endpoint is configured with right now. Endpoints deleted since the benchmark have no API row. -#}
with api as (
    select endpoint_id, flashboot as api_flashboot, name, polled_at_utc as api_polled_at_utc
    from {{ ref('silver_runpod_endpoints') }}
    qualify row_number() over (partition by endpoint_id order by poll_seq desc) = 1
)
select
    g.engine, g.model, g.endpoint_id,
    g.flashboot_setting                     as benchmark_flashboot,
    a.api_flashboot,
    case
        when a.endpoint_id is null                                  then 'endpoint no longer exists'
        when g.flashboot_setting = 'unknown'                        then 'api fills a gap'
        when upper(g.flashboot_setting) = 'ON'  and a.api_flashboot in ('FLASHBOOT', 'PRIORITY_FLASHBOOT') then 'agree'
        when upper(g.flashboot_setting) = 'OFF' and a.api_flashboot = 'OFF'                                 then 'agree'
        else 'disagree'
    end                                     as verdict,
    g.n_cold, g.n_hits, g.hit_rate, a.name, a.api_polled_at_utc,
    sysdate()                               as gold_built_at
from {{ ref('gold_flashboot_hit_rate') }} g
left join api a on a.endpoint_id = g.endpoint_id
order by g.engine, g.model, g.endpoint_id
