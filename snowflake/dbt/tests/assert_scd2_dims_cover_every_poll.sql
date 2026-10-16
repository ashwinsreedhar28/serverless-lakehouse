{{ config(tags=['runpod']) }}
{#- Coverage, the check scd2_windows cannot make on these two models (their valid_to is the next row's valid_from by
    construction):
      - every poll × endpoint observation falls in exactly one version of dim_runpod_endpoint, and that version holds
        exactly the config the poll saw;
      - for endpoints that have release history, every observation falls in exactly one version of
        dim_runpod_endpoint_release (an endpoint with none — its /releases fetch never succeeded — is
        assert_release_history_present's warning, not a reconstruction defect);
      - current rows agree with the polls, not with the dimension's own is_deleted: an endpoint in the latest complete
        listing, or seen after it, has exactly one current row in each dimension; any other endpoint has none. -#}
with obs as (
    select poll_id, endpoint_id, polled_at_utc, config_hash from {{ ref('silver_runpod_endpoint_config') }}
),
with_history as (
    select distinct endpoint_id from {{ ref('silver_runpod_releases') }}
),
poll_cov as (
    select o.poll_id, o.endpoint_id,
           count(d.endpoint_id) as n_versions, count_if(d.config_hash = o.config_hash) as n_same_config
    from obs o
    left join {{ ref('dim_runpod_endpoint') }} d
      on d.endpoint_id = o.endpoint_id
     and o.polled_at_utc >= d.valid_from_utc and o.polled_at_utc < coalesce(d.valid_to_utc, '9999-12-31'::timestamp_ntz)
    group by 1, 2
),
release_cov as (
    select o.poll_id, o.endpoint_id, count(d.endpoint_id) as n_versions
    from obs o
    join with_history h on h.endpoint_id = o.endpoint_id
    left join {{ ref('dim_runpod_endpoint_release') }} d
      on d.endpoint_id = o.endpoint_id
     and o.polled_at_utc >= d.valid_from_utc and o.polled_at_utc < coalesce(d.valid_to_utc, '9999-12-31'::timestamp_ntz)
    group by 1, 2
),
latest_complete as (
    select max(polled_at_utc) as t from {{ ref('silver_runpod_polls') }} where endpoints_complete
),
expected_current as (
    -- from the observations alone: listed in the latest complete poll, or seen after it
    select o.endpoint_id,
           boolor_agg(o.endpoint_id in (select endpoint_id from {{ ref('silver_runpod_endpoint_current') }})
                      or o.polled_at_utc > (select t from latest_complete)) as should_be_current
    from obs o
    group by 1
),
current_rows as (
    select 'dim_runpod_endpoint' as dim, endpoint_id, count_if(is_current) as n_current
    from {{ ref('dim_runpod_endpoint') }} group by 1, 2
    union all
    select 'dim_runpod_endpoint_release', endpoint_id, count_if(is_current)
    from {{ ref('dim_runpod_endpoint_release') }} group by 1, 2
)
select 'dim_runpod_endpoint' as dim, endpoint_id, poll_id,
       'observation in ' || n_versions || ' versions, ' || n_same_config || ' with its config' as problem
from poll_cov where n_versions <> 1 or n_same_config <> 1
union all
select 'dim_runpod_endpoint_release', endpoint_id, poll_id, 'observation in ' || n_versions || ' versions'
from release_cov where n_versions <> 1
union all
select c.dim, c.endpoint_id, null,
       c.n_current || ' current rows; the polls say ' || iff(e.should_be_current, 'it exists', 'it is gone')
from current_rows c
join expected_current e on e.endpoint_id = c.endpoint_id
where c.n_current <> iff(e.should_be_current, 1, 0)
