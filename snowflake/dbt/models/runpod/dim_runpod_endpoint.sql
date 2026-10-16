{{ config(schema='SILVER') }}
{#- SCD Type 2 over every poll: one row per endpoint × config version, valid over the half-open window
    [valid_from_utc, valid_to_utc). A version starts at the first poll whose config_hash differs from the poll before
    (endpoint_tracked_cols()); A→B→A is three versions, not two. This is the check strategy rebuilt from the whole poll
    history instead of sampled at `dbt snapshot` time, so it can be dropped and rebuilt from bronze at any point.

    Sampling limit, stated in the columns: the change happened somewhere in (changed_after_utc, valid_from_utc], the
    gap between the last poll of the previous version and the first poll of this one, and anything changed and changed
    back inside that gap is invisible. For image / GPU / CUDA floor dim_runpod_endpoint_release has the exact times.

    An endpoint missing from a *complete* listing after its last sighting was deleted: its last version closes at that
    poll and is_deleted is set. A poll whose listing failed part-way (endpoints_complete false) still contributes the
    configs it did see, but is never evidence of a deletion. -#}
{%- set cols = endpoint_tracked_cols() %}
with complete_polls as (
    select polled_at_utc from {{ ref('silver_runpod_polls') }} where endpoints_complete
),
obs as (
    select c.*, row_number() over (partition by c.endpoint_id order by c.polled_at_utc, c.poll_id) as seq
    from {{ ref('silver_runpod_endpoint_config') }} c
),
flagged as (
    select *, coalesce(config_hash <> lag(config_hash) over (partition by endpoint_id order by seq), true) as starts_version
    from obs
),
numbered as (
    select *, sum(iff(starts_version, 1, 0)) over (partition by endpoint_id order by seq
                                                   rows between unbounded preceding and current row) as version_no
    from flagged
),
versions as (
    -- every poll in a version has the same tracked values (same hash), so any_value is exact
    select endpoint_id, version_no,
           min(polled_at_utc) as valid_from_utc, max(polled_at_utc) as last_seen_utc, count(*) as n_polls,
           {% for c in cols %}any_value({{ c }}) as {{ c }}, {% endfor %}any_value(config_hash) as config_hash
    from numbered
    group by 1, 2
),
gone as (
    -- the first complete listing after the last sighting (it cannot contain the endpoint, or that would be the last sighting)
    select l.endpoint_id, min(p.polled_at_utc) as deleted_at_utc
    from (select endpoint_id, max(polled_at_utc) as last_seen_utc from obs group by 1) l
    join complete_polls p on p.polled_at_utc > l.last_seen_utc
    group by 1
),
type1 as (
    -- current-value columns: the latest poll's, on every version row
    select endpoint_id, name as current_name, workers_min as current_workers_min, workers_max as current_workers_max
    from obs
    qualify row_number() over (partition by endpoint_id order by seq desc) = 1
),
windows as (
    select v.*,
           lag(v.last_seen_utc) over (partition by v.endpoint_id order by v.version_no)    as changed_after_utc,
           lead(v.valid_from_utc) over (partition by v.endpoint_id order by v.version_no)  as next_valid_from_utc,
           g.deleted_at_utc
    from versions v
    left join gone g on g.endpoint_id = v.endpoint_id
)
select
    md5(w.endpoint_id || '|' || to_varchar(w.valid_from_utc, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))   as endpoint_version_key,
    w.endpoint_id, w.version_no,
    w.valid_from_utc,
    coalesce(w.next_valid_from_utc, w.deleted_at_utc)                                         as valid_to_utc,
    w.next_valid_from_utc is null and w.deleted_at_utc is null                                as is_current,
    w.next_valid_from_utc is null and w.deleted_at_utc is not null                            as is_deleted,
    w.changed_after_utc,
    datediff('minute', w.changed_after_utc, w.valid_from_utc)                                 as change_window_min,
    {% for c in cols %}w.{{ c }}, {% endfor %}
    w.config_hash, w.n_polls, w.last_seen_utc,
    t.current_name, t.current_workers_min, t.current_workers_max,
    sysdate()                                                                                 as silver_built_at
from windows w
join type1 t on t.endpoint_id = w.endpoint_id
