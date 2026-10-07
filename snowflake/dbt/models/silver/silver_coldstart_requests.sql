{#-
One Serverless request (cold or warm) from either source, typed, deduped, joined to the seeds.
Port of lakehouse.silver.build_coldstart_requests: emberserve_requests ∪ pulse_requests, then the derived fields.
-#}

with runs as (
    {{ current_snapshot('bronze_coldstart_runs') }}
),

-- emberserve: every run row holds a cold and a warm request as JSON strings; one output row each
emberserve_pairs as (
    -- bronze's own `kind` column ("serverless_coldstart") gives way to the request kind, as in Spark's withColumn
    select r.* exclude (kind), 'cold' as kind, try_parse_json(r.cold_json) as j from runs r
    union all
    select r.* exclude (kind), 'warm' as kind, try_parse_json(r.warm_json) as j from runs r
),

emberserve as (
    select
        'emberserve_results'                                        as source,
        coalesce(s.engine, 'emberserve')                            as engine,
        s.engine_build,
        e.label                                                     as series_label,
        e.endpoint                                                  as endpoint_id,
        e.run_index::int                                            as run_index,
        null::int                                                   as request_index,
        e.kind,
        {{ epoch_s_to_ts('e.j:submit_wall') }}                      as request_ts_utc,
        s.model                                                     as model,
        s.gpu_model                                                 as gpu_label,
        s.gpu_model                                                 as gpu_label_raw,
        null::string                                                as gpu_label_override_note,
        s.gpu_model,
        g.tier                                                      as gpu_tier,
        g.price_per_hr_usd,
        coalesce(s.flashboot, 'unknown')                            as flashboot,
        s.weights_mode,
        e.j:status::int                                             as http_status,
        e.j:job_status::string                                      as job_status,
        coalesce(e.j:ok::boolean, false)                            as ok,
        e.j:total_s::double * 1000                                  as wall_ms,
        e.j:delay_ms::number                                        as delay_ms,
        e.j:execution_ms::number                                    as exec_ms,
        e.j:worker_id::string                                       as worker_id,
        null::number                                                as prompt_tokens,
        null::number                                                as completion_tokens,
        -- the engine's own word, where it wrote one; null means "not recorded", not "no resume"
        e.j:flashboot_resume::boolean                               as flashboot_resume_recorded,
        coalesce(n.host_state, 'unknown')                           as host_state,
        n.note                                                      as run_note,
        e.health_before_json                                        as workers_before_json,
        {{ variant_text('e.j:error') }}                             as error,
        e.source_file, e.source_sha256,
        e.run_label                                                 as bronze_run_label
    from emberserve_pairs e
    left join {{ ref('dim_coldstart_series') }} s on s.series_label = e.label
    -- emberserve series are keyed to a GPU model; the price lives on the matching gpu_labels seed row
    left join {{ ref('dim_gpu_label') }} g on g.gpu_label = s.gpu_model
    left join {{ ref('dim_coldstart_run_notes') }} n on n.series_label = e.label and n.run_index = e.run_index
),

-- Pulse coldstart.py rows: three files; results_v0.csv and bench/logs/results_runs1-3.csv are byte-identical copies of runs 1-3
pulse_raw as (
    {{ current_snapshot('bronze_pulse_coldstart_requests') }}
),

pulse_dedup as (
    select *
    from pulse_raw
    qualify row_number() over (
        partition by ts_utc, endpoint_id, kind, cycle, req, delay_ms, exec_ms
        order by iff(source_file = 'pulse/results.csv', 0, 1), source_file
    ) = 1
),

pulse_labelled as (
    -- A label is what the operator typed on the command line, not what Runpod placed the job on. Where the placement notes
    -- say otherwise for a specific request, the override seed wins and the raw label is kept beside it. Compared as
    -- timestamps, not strings, so a re-export that writes "Z" instead of "+00:00" still matches the seed.
    select
        p.*,
        coalesce(ov.gpu_label, p.gpu)                               as label_resolved,
        ov.note                                                     as gpu_label_override_note
    from pulse_dedup p
    left join {{ ref('dim_coldstart_request_overrides') }} ov
      on ov.endpoint_id = p.endpoint_id
     and {{ to_utc('ov.ts_utc') }} = {{ to_utc('p.ts_utc') }}
),

pulse as (
    select
        'pulse_coldstart'                                           as source,
        'worker-vllm'                                               as engine,
        null::string                                                as engine_build,
        null::string                                                as series_label,
        p.endpoint_id,
        try_to_number(p.cycle)::int                                 as run_index,
        try_to_number(p.req)::int                                   as request_index,
        p.kind,
        {{ to_utc('p.ts_utc') }}                                    as request_ts_utc,
        {{ canonical_model('p.model') }}                            as model,
        p.label_resolved                                            as gpu_label,
        p.gpu                                                       as gpu_label_raw,
        p.gpu_label_override_note,
        g.gpu_model,
        g.tier                                                      as gpu_tier,
        g.price_per_hr_usd,
        'unknown'                                                   as flashboot,
        iff(contains(p.label_resolved, 'vol'), 'volume', 'fetched') as weights_mode,
        iff(regexp_like(p.status, $$\d+$$), try_to_number(p.status)::int, null)    as http_status,
        iff(not regexp_like(p.status, $$\d+$$), p.status, null)                     as job_status,
        p.status = 'COMPLETED'                                      as ok,
        try_to_double(p.wall_ms)                                    as wall_ms,
        try_to_number(p.delay_ms)                                   as delay_ms,
        try_to_number(p.exec_ms)                                    as exec_ms,
        null::string                                                as worker_id,
        try_to_number(p.prompt_tokens)                              as prompt_tokens,
        try_to_number(p.completion_tokens)                          as completion_tokens,
        null::boolean                                               as flashboot_resume_recorded,
        'unknown'                                                   as host_state,
        null::string                                                as run_note,
        {{ nz('p.workers_before') }}                                as workers_before_json,
        {{ nz('p.error') }}                                         as error,
        p.source_file, p.source_sha256,
        p.run_label                                                 as bronze_run_label
    from pulse_labelled p
    left join {{ ref('dim_gpu_label') }} g on g.gpu_label = p.label_resolved
),

unioned as (
    select * from emberserve
    union all
    select * from pulse
),

derived as (
    select
        u.*,
        -- a cold request answered under the threshold was a resume or a still-warm worker, not a full boot
        case when kind = 'cold' then (ok and delay_ms < {{ var('flashboot_hit_ms') }}) end     as is_flashboot_hit,
        -- request_duration_s is a cost *proxy*, not billed time: Runpod bills worker start, execution and idle phases per
        -- worker, which a per-request sum neither bounds from above nor below.
        case when ok then (coalesce(delay_ms, 0) + coalesce(exec_ms, 0)) / 1000.0 end           as request_duration_s
    from unioned u
)

select
    source, engine, engine_build, series_label, endpoint_id, run_index, request_index, kind,
    request_ts_utc, model, gpu_label, gpu_label_raw, gpu_label_override_note, gpu_model, gpu_tier,
    price_per_hr_usd, flashboot,
    weights_mode, http_status, job_status, ok, wall_ms, delay_ms, exec_ms, worker_id,
    prompt_tokens, completion_tokens, is_flashboot_hit, flashboot_resume_recorded, request_duration_s,
    request_duration_s / 3600.0 * price_per_hr_usd                  as est_cost_usd,
    host_state, run_note, workers_before_json, error, source_file, source_sha256, bronze_run_label,
    sysdate()                                                       as silver_built_at
from derived
