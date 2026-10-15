{{ config(schema='SILVER') }}
{#- SCD Type 2 from Runpod's release log: one row per endpoint × version of the release-tracked columns (image, GPU
    selection, CUDA floor, allowed CUDA, data centers, disk), valid over [valid_from_utc, valid_to_utc) where valid_from
    is the release's own createdAt. This is the timestamp strategy: the source says when each change happened, so no
    version is missed between polls and no start time is late by a poll interval.

    Releases are diffs, not full states (version 1 often only sets the name), so each column is rebuilt per release:
      1. the `new` of the latest diff of that column at or before this release, else
      2. the `old` of the earliest diff after it (the value it held until that change), else
      3. the value the latest poll sees (the column never changed in the whole log).
    A diff to or from null is carried through the fill as '<unset>' so it is not mistaken for "no diff here".
    Consecutive releases that leave every tracked column unchanged (env or registry-auth edits) collapse into one version.
    assert_release_dim_matches_every_poll checks the rebuild against what every poll actually saw.

    Deletion is not in the release log; a deleted endpoint's last version closes when dim_runpod_endpoint saw it gone. -#}
{%- set cols = release_tracked_cols() %}
with rel as (select * from {{ ref('silver_runpod_releases') }}),
releases as (
    select distinct endpoint_id, release_version, created_at_utc from rel
),
cols as (
    select column1 as column_name from values {% for c in cols %}('{{ c }}'){{ ', ' if not loop.last }}{% endfor %}
),
diffs as (
    select endpoint_id, release_version, column_name, old_value, new_value
    from rel
    where column_name is not null
    qualify row_number() over (partition by endpoint_id, release_version, column_name order by field) = 1
),
grid as (
    select r.endpoint_id, r.release_version, r.created_at_utc, c.column_name,
           d.column_name is not null as has_diff, d.old_value, d.new_value
    from releases r
    cross join cols c
    left join diffs d
      on d.endpoint_id = r.endpoint_id and d.release_version = r.release_version and d.column_name = c.column_name
),
filled as (
    select g.*,
        last_value(iff(has_diff, coalesce(new_value, '<unset>'), null)) ignore nulls over (
            partition by endpoint_id, column_name order by release_version
            rows between unbounded preceding and current row)                              as value_from_new,
        -- descending order: the closest release at or after this one that changed the column, and what it changed from
        last_value(iff(has_diff, coalesce(old_value, '<unset>'), null)) ignore nulls over (
            partition by endpoint_id, column_name order by release_version desc
            rows between unbounded preceding and current row)                              as value_from_old
    from grid g
),
cur as (
    select * from {{ ref('silver_runpod_endpoint_config') }}
    qualify row_number() over (partition by endpoint_id order by poll_seq desc) = 1
),
valued as (
    select f.endpoint_id, f.release_version, f.created_at_utc, f.column_name,
           nullif(coalesce(f.value_from_new, f.value_from_old,
                    case f.column_name {% for c in cols %}when '{{ c }}' then k.{{ c }} {% endfor %}end), '<unset>') as value
    from filled f
    left join cur k on k.endpoint_id = f.endpoint_id
),
wide as (
    select endpoint_id, release_version, created_at_utc,
           {% for c in cols %}max(iff(column_name = '{{ c }}', value, null)) as {{ c }}{{ ',' if not loop.last }}
           {% endfor %}
    from valued
    group by 1, 2, 3
),
hashed as (
    select *, {{ scd2_hash(cols) }} as config_hash from wide
),
flagged as (
    select *, coalesce(config_hash <> lag(config_hash) over (partition by endpoint_id order by release_version), true) as starts_version
    from hashed
),
numbered as (
    select *, sum(iff(starts_version, 1, 0)) over (partition by endpoint_id order by release_version
                                                   rows between unbounded preceding and current row) as version_no
    from flagged
),
versions as (
    select endpoint_id, version_no,
           min(release_version) as release_from, max(release_version) as release_to, count(*) as n_releases,
           min(created_at_utc) as valid_from_utc,
           {% for c in cols %}any_value({{ c }}) as {{ c }}, {% endfor %}any_value(config_hash) as config_hash
    from numbered
    group by 1, 2
),
deleted as (
    select endpoint_id, valid_to_utc as deleted_at_utc from {{ ref('dim_runpod_endpoint') }} where is_deleted
),
windows as (
    select v.*, lead(v.valid_from_utc) over (partition by v.endpoint_id order by v.version_no) as next_valid_from_utc,
           d.deleted_at_utc
    from versions v
    left join deleted d on d.endpoint_id = v.endpoint_id
)
select
    md5(endpoint_id || '|' || to_varchar(valid_from_utc, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))   as endpoint_release_key,
    endpoint_id, version_no, release_from, release_to, n_releases,
    valid_from_utc,
    coalesce(next_valid_from_utc, deleted_at_utc)                                         as valid_to_utc,
    next_valid_from_utc is null and deleted_at_utc is null                                as is_current,
    next_valid_from_utc is null and deleted_at_utc is not null                            as is_deleted,
    {% for c in cols %}{{ c }}, {% endfor %}config_hash,
    sysdate()                                                                             as silver_built_at
from windows
