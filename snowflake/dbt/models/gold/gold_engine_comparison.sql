{#-
Same GPU, same model: what does each engine cost you on a cold start, and what does warm look like?

Two kinds of row, told apart by `scope`: `pooled` aggregates every full boot of that engine × weights mode; one row per
`cohort` splits them by host state and data era, because a pooled median mixes a fresh host that had to pull the image,
same-night reruns on a warm host, and the Sep 23 Pulse-era runs. The cohort rows sum to the pooled row (a cohort with warm
requests but no full boot keeps its row with n_full_boots = 0). Port of lakehouse.gold.engine_comparison.
-#}

with same as (
    select
        *,
        case
            when host_state != 'unknown'        then host_state
            when source = 'pulse_coldstart'     then 'pulse_sep23_host_unknown'
            else 'host_unknown'
        end as cohort
    from {{ ref('silver_coldstart_requests') }}
    where ok and model = 'Qwen3-8B' and gpu_model = 'RTX 4090'
),

cold_full as (
    select * from same where kind = 'cold' and not coalesce(is_flashboot_hit, false)
),

warm as (
    select * from same where kind = 'warm'
),

{%- for scope, keys in [('pooled', ['engine', 'weights_mode']), ('cohort', ['engine', 'weights_mode', 'cohort'])] %}
{%- set klist = keys | join(', ') %}

cold_{{ scope }} as (
    select
        {{ klist }},
        count(*)                                                        as n_full_boots,
        {{ pct('delay_ms', 0.5) }}                                      as cold_delay_ms_p50,
        round(avg(delay_ms))::number(38, 0)                             as cold_delay_ms_mean,
        min(delay_ms)                                                   as cold_delay_ms_min,
        max(delay_ms)                                                   as cold_delay_ms_max,
        {{ pct('exec_ms', 0.5) }}                                       as cold_exec_ms_p50,
        {{ pct('est_cost_usd', 0.5) }}                                  as cold_est_cost_usd_p50,
        array_sort(array_agg(distinct series_label))                    as series,
        array_sort(array_agg(distinct to_char(request_ts_utc, 'YYYY-MM-DD')))   as dates,
        sum(iff(request_ts_utc is null, 1, 0))                          as n_undated
    from cold_full
    group by {{ klist }}
),

warm_{{ scope }} as (
    select
        {{ klist }},
        count(*)                                                        as n_warm,
        {{ pct('delay_ms', 0.5) }}                                      as warm_delay_ms_p50,
        {{ pct('exec_ms', 0.5) }}                                       as warm_exec_ms_p50
    from warm
    group by {{ klist }}
),

rows_{{ scope }} as (
    select
        {%- for k in keys %}
        coalesce(c.{{ k }}, w.{{ k }})                                  as {{ k }},
        {%- endfor %}
        '{{ scope }}'                                                   as scope,
        {%- if scope == 'pooled' %}
        'all runs (pooled)'                                             as cohort,
        {%- endif %}
        coalesce(c.n_full_boots, 0)                                     as n_full_boots,
        coalesce(c.n_undated, 0)                                        as n_undated,
        c.cold_delay_ms_p50, c.cold_delay_ms_mean, c.cold_delay_ms_min, c.cold_delay_ms_max,
        c.cold_exec_ms_p50, c.cold_est_cost_usd_p50,
        coalesce(w.n_warm, 0)                                           as n_warm,
        w.warm_delay_ms_p50, w.warm_exec_ms_p50,
        c.series, c.dates
    from cold_{{ scope }} c
    full outer join warm_{{ scope }} w
      on {% for k in keys %}{% if not loop.first %} and {% endif %}c.{{ k }} = w.{{ k }}{% endfor %}
),
{%- endfor %}

unioned as (
    select engine, weights_mode, scope, cohort, n_full_boots, n_undated, cold_delay_ms_p50, cold_delay_ms_mean,
           cold_delay_ms_min, cold_delay_ms_max, cold_exec_ms_p50, cold_est_cost_usd_p50, n_warm,
           warm_delay_ms_p50, warm_exec_ms_p50, series, dates
    from rows_pooled
    union all
    select engine, weights_mode, scope, cohort, n_full_boots, n_undated, cold_delay_ms_p50, cold_delay_ms_mean,
           cold_delay_ms_min, cold_delay_ms_max, cold_exec_ms_p50, cold_est_cost_usd_p50, n_warm,
           warm_delay_ms_p50, warm_exec_ms_p50, series, dates
    from rows_cohort
)

select *, sysdate() as gold_built_at
from unioned
order by engine, weights_mode, iff(scope = 'pooled', 0, 1), cohort
