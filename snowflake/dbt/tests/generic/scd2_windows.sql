{#- The SCD Type 2 window invariants, per key: windows are non-empty, at most one row is open (valid_to null), only the
    last row may be open, and each row ends exactly where the next begins (no gap, no overlap). Half-open windows
    [valid_from, valid_to) then put every instant in at most one version. Returns one row per violation. -#}
{% test scd2_windows(model, key, valid_from='valid_from_utc', valid_to='valid_to_utc') %}
with w as (
    select
        {{ key }} as k, {{ valid_from }} as vf, {{ valid_to }} as vt,
        lead({{ valid_from }}) over (partition by {{ key }} order by {{ valid_from }}) as next_vf,
        count_if({{ valid_to }} is null) over (partition by {{ key }}) as n_open
    from {{ model }}
),
checked as (
    select *,
        case
            when vt is not null and vt <= vf                then 'empty or inverted window'
            when n_open > 1                                 then 'more than one open row'
            when next_vf is not null and vt is null         then 'open row is not the last'
            when next_vf is not null and vt > next_vf       then 'overlaps the next version'
            when next_vf is not null and vt < next_vf       then 'gap before the next version'
        end as violation
    from w
)
select * from checked where violation is not null
{% endtest %}
