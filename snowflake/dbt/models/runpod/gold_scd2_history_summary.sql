{{ config(schema='GOLD') }}
{#- The figures the README quotes about the endpoint-config histories, computed from what is in bronze (every poll,
    from the Mac and the GitHub poller), one row per metric so the README and this table cannot drift apart. -#}
{%- set rcols = release_tracked_cols() %}
with polls as (
    select min(polled_at_utc) as first_poll_utc, max(polled_at_utc) as last_poll_utc, count(*) as n_polls
    from {{ ref('silver_runpod_polls') }} where n_endpoints > 0
),
obs as (select * from {{ ref('silver_runpod_endpoint_config') }}),
rebuild as (
    select count(*) as n_obs,
           count_if(r.endpoint_id is not null {% for c in rcols %}and equal_null(o.{{ c }}, r.{{ c }}) {% endfor %}) as n_match
    from obs o
    left join {{ ref('dim_runpod_endpoint_release') }} r
      on r.endpoint_id = o.endpoint_id
     and o.polled_at_utc >= r.valid_from_utc and o.polled_at_utc < coalesce(r.valid_to_utc, '9999-12-31'::timestamp_ntz)
),
poll_versions as (
    select *, {{ scd2_hash(rcols) }} as release_cols_hash from {{ ref('dim_runpod_endpoint') }}
),
poll_release_changes as (
    -- versions after an endpoint's first whose release-tracked columns differ from the version before
    select count(*) as n
    from (select release_cols_hash, lag(release_cols_hash) over (partition by endpoint_id order by version_no) as prev_hash
          from poll_versions)
    where prev_hash is not null and release_cols_hash <> prev_hash
),
log_release_changes as (
    -- release-log versions (each one a change to a release-tracked column) that started inside the polled window
    select count(*) as n
    from {{ ref('dim_runpod_endpoint_release') }} r, polls p
    where r.version_no > 1 and r.valid_from_utc > p.first_poll_utc and r.valid_from_utc <= p.last_poll_utc
),
counts as (
    select 'polls' as history, count(*) as n_versions, count(distinct endpoint_id) as n_endpoints,
           count_if(is_current) as n_current, count_if(is_deleted) as n_deleted
    from {{ ref('dim_runpod_endpoint') }}
    union all
    select 'release log', count(*), count(distinct endpoint_id), count_if(is_current), count_if(is_deleted)
    from {{ ref('dim_runpod_endpoint_release') }}
    union all
    select 'dbt snapshot', count(*), count(distinct endpoint_id), count_if(dbt_valid_to is null), null
    from {{ ref('snap_runpod_endpoint_config') }}
)
select ord, metric, value, detail, sysdate() as gold_built_at
from (
    select 1 as ord, 'polls in bronze' as metric, n_polls as value,
           to_varchar(first_poll_utc, 'YYYY-MM-DD HH24:MI') || ' to ' || to_varchar(last_poll_utc, 'YYYY-MM-DD HH24:MI') || ' UTC' as detail
    from polls
    union all select 2, 'poll x endpoint observations', n_obs, null from rebuild
    union all select 3, 'observations the release rebuild matches on all six release columns', n_match, null from rebuild
    union all select 4, 'changes to release-tracked columns the polls saw', n, 'in the polled window' from poll_release_changes
    union all select 5, 'changes to release-tracked columns in the release log', n, 'same window' from log_release_changes
    {%- for h, o in [('polls', 6), ('release log', 7), ('dbt snapshot', 8)] %}
    union all select {{ o }}, '{{ h }}: versions', n_versions,
                     n_endpoints || ' endpoints, ' || n_current || ' current' || coalesce(', ' || n_deleted || ' deleted', '')
              from counts where history = '{{ h }}'
    {%- endfor %}
)
order by ord
