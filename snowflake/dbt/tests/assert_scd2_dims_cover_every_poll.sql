{{ config(tags=['runpod']) }}
{#- Coverage, the check scd2_windows cannot make on these two models (their valid_to is the next row's valid_from by
    construction): every poll × endpoint observation falls in exactly one version of each dimension, the poll-built
    version holds exactly the config that poll saw, and every endpoint has exactly one current row unless it was
    deleted (then none). -#}
with obs as (
    select poll_id, endpoint_id, polled_at_utc, config_hash from {{ ref('silver_runpod_endpoint_config') }}
),
poll_cov as (
    select o.poll_id, o.endpoint_id, o.polled_at_utc,
           count(d.endpoint_id) as n_versions, count_if(d.config_hash = o.config_hash) as n_same_config
    from obs o
    left join {{ ref('dim_runpod_endpoint') }} d
      on d.endpoint_id = o.endpoint_id
     and o.polled_at_utc >= d.valid_from_utc and o.polled_at_utc < coalesce(d.valid_to_utc, '9999-12-31'::timestamp_ntz)
    group by 1, 2, 3
),
release_cov as (
    select o.poll_id, o.endpoint_id, o.polled_at_utc, count(d.endpoint_id) as n_versions
    from obs o
    left join {{ ref('dim_runpod_endpoint_release') }} d
      on d.endpoint_id = o.endpoint_id
     and o.polled_at_utc >= d.valid_from_utc and o.polled_at_utc < coalesce(d.valid_to_utc, '9999-12-31'::timestamp_ntz)
    group by 1, 2, 3
),
current_rows as (
    select 'dim_runpod_endpoint' as dim, endpoint_id, count_if(is_current) as n_current, boolor_agg(is_deleted) as deleted
    from {{ ref('dim_runpod_endpoint') }} group by 1, 2
    union all
    select 'dim_runpod_endpoint_release', endpoint_id, count_if(is_current), boolor_agg(is_deleted)
    from {{ ref('dim_runpod_endpoint_release') }} group by 1, 2
)
select 'dim_runpod_endpoint' as dim, endpoint_id, poll_id, 'observation in ' || n_versions || ' versions, '
       || n_same_config || ' with its config' as problem
from poll_cov where n_versions <> 1 or n_same_config <> 1
union all
select 'dim_runpod_endpoint_release', endpoint_id, poll_id, 'observation in ' || n_versions || ' versions'
from release_cov where n_versions <> 1
union all
select dim, endpoint_id, null, n_current || ' current rows' || iff(deleted, ' for a deleted endpoint', '')
from current_rows where n_current <> iff(deleted, 0, 1)
