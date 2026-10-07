{#-
One (series, run, phase) from emberserve's startup timeline: the `phases_s` durations and the `timeline.marks` instants
the engine wrote into each cold request. Port of lakehouse.silver.build_coldstart_phases.
-#}

with runs as (
    {{ current_snapshot('bronze_coldstart_runs') }}
),

docs as (
    select
        label                                   as series_label,
        endpoint                                as endpoint_id,
        run_index::int                          as run_index,
        try_parse_json(cold_json)               as j,
        source_file, source_sha256,
        run_label                               as bronze_run_label
    from runs
),

phases as (
    select
        d.series_label, d.endpoint_id, d.run_index,
        d.j:worker_id::string                   as worker_id,
        'phase'                                 as kind,
        f.key                                   as name,
        f.value::double                         as seconds,
        null::timestamp_ntz                     as mark_ts_utc,
        d.source_file, d.source_sha256, d.bronze_run_label
    from docs d,
    lateral flatten(input => d.j:phases_s) f
),

marks as (
    select
        d.series_label, d.endpoint_id, d.run_index,
        d.j:worker_id::string                   as worker_id,
        'mark'                                  as kind,
        f.key                                   as name,
        null::double                            as seconds,
        {{ epoch_s_to_ts('f.value') }}          as mark_ts_utc,
        d.source_file, d.source_sha256, d.bronze_run_label
    from docs d,
    lateral flatten(input => d.j:timeline:marks) f
)

select *, sysdate() as silver_built_at from phases
union all
select *, sysdate() as silver_built_at from marks
