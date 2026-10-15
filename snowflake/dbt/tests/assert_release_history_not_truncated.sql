{{ config(severity='warn', tags=['runpod']) }}
{#- tools/runpod_poll.py reads the first page of /releases only. If an endpoint's history ever spans a second page,
    its oldest diffs stop arriving and dim_runpod_endpoint_release loses the start of that history. -#}
select endpoint_id, max(release_version) as latest_release_version
from {{ ref('silver_runpod_releases') }}
where history_truncated
group by 1
