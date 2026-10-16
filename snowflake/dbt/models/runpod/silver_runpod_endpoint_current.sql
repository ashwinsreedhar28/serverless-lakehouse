{{ config(schema='SILVER') }}
{#- The config of every endpoint in the latest poll whose endpoint listing completed: the input to
    snap_runpod_endpoint_config, and the independent "which endpoints exist now" that assert_scd2_dims_cover_every_poll
    checks the dimensions' current rows against. A dbt snapshot only ever sees its input as it is when `dbt snapshot`
    runs, so the input is "now", and an endpoint missing from it is a hard delete (hard_deletes: invalidate). -#}
with latest as (
    select poll_id from {{ ref('silver_runpod_polls') }}
    where endpoints_complete
    qualify row_number() over (order by polled_at_utc desc, poll_id desc) = 1
)
select c.*
from {{ ref('silver_runpod_endpoint_config') }} c
join latest l on l.poll_id = c.poll_id
