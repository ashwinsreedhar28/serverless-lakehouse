{{ config(severity='warn', tags=['runpod']) }}
{#- An endpoint the polls have seen but whose /releases never came back (every fetch failed, e.g. a brand-new endpoint
    polled once during an API error) has no release history, so dim_runpod_endpoint_release cannot describe it. Usually
    fixed by the next poll; a warning, not a reconstruction defect. -#}
select o.endpoint_id, count(*) as n_observations, max(o.polled_at_utc) as last_seen_utc
from {{ ref('silver_runpod_endpoint_config') }} o
where o.endpoint_id not in (select endpoint_id from {{ ref('silver_runpod_releases') }})
group by 1
