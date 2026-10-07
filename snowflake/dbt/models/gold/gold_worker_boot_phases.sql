{#-
worker-vllm's own account of a boot, from the log lines vLLM prints while starting. Port of lakehouse.gold.worker_boot_phases.

A boot opens at the wrapper's "Starting vLLM: vllm serve ..." line. vLLM prints exactly one "Initializing a V1 LLM engine"
per engine start, so an init with no unmatched wrapper line before it on the same worker opens a boot too (console exports
can miss the wrapper line: endpoint_logs_1450-1553 has one start line for three boots). Lines before any opener are boot 0
and are kept only when they carry boot phases (run1_cold_worker_404.log starts mid-boot). vLLM's own "Starting vLLM server
on http://..." comes ~2 min later and must not open anything. A console export can interleave several workers, so segment
per worker.
-#}

with ev as (
    select
        *,
        coalesce(worker_id, '')                                         as wk,
        startswith(message, 'Starting vLLM: ')                          as is_start,
        startswith(message, 'Initializing a V1 LLM engine')             as is_init,
        startswith(message, 'Graph capturing finished')                 as is_graph
    from {{ ref('silver_worker_log_events') }}
),

counted as (
    select
        *,
        sum(iff(is_start, 1, 0)) over (partition by source_file, wk order by line_no rows between unbounded preceding and current row) as n_start,
        sum(iff(is_init, 1, 0))  over (partition by source_file, wk order by line_no rows between unbounded preceding and current row) as n_init
    from ev
),

segmented as (
    select
        *,
        n_start + sum(iff(is_init and n_init > n_start, 1, 0))
                      over (partition by source_file, wk order by line_no rows between unbounded preceding and current row) as boot_index
    from counted
),

boots as (
    select
        source_file, wk, boot_index,
        min(worker_id)                                                              as worker_id,
        min(ts_format)                                                              as ts_format,
        case
            when sum(iff(is_start, 1, 0)) > 0 then 'Starting vLLM: (wrapper)'
            when sum(iff(is_init, 1, 0)) > 0  then 'Initializing a V1 LLM engine (no wrapper line captured)'
            else 'none (log starts mid-boot)'
        end                                                                         as segmented_by,
        min(iff(is_start, ts_utc, null))                                            as t_start_vllm,
        min(iff(startswith(message, 'Loading weights took'), ts_utc, null))         as t_weights_loaded,
        min(iff(startswith(message, 'Application startup complete'), ts_utc, null)) as t_api_ready,
        min(iff(startswith(message, '--- Starting Serverless Worker'), ts_utc, null)) as t_sdk_started,
        max(iff(startswith(message, 'Loading weights took'), {{ log_num('Loading weights took ([0-9.]+) seconds') }}, null))   as weights_load_s,
        max(iff(startswith(message, 'Model loading took'),   {{ log_num('Model loading took ([0-9.]+) GiB') }}, null))         as model_gib,
        max(iff(startswith(message, 'Model loading took'),   {{ log_num('and ([0-9.]+) seconds') }}, null))                    as model_load_s,
        max(iff(startswith(message, 'torch.compile took'),   {{ log_num('torch\\.compile took ([0-9.]+) s') }}, null))         as torch_compile_s,
        -- vLLM 0.30 captures CUDA graphs in two passes and prints "Graph capturing finished" once per pass: the boot paid
        -- for both, so sum them (max would report the larger pass as if it were the whole)
        sum(iff(is_graph, {{ log_num('finished in ([0-9.]+) secs') }}, null))                                                  as graph_capture_s,
        sum(iff(is_graph, 1, 0))                                                                                           as n_graph_passes,
        max(iff(startswith(message, 'init engine'), {{ log_num('took ([0-9.]+) s') }}, null))                                  as init_engine_s,
        max(iff(startswith(message, 'init engine'), {{ log_num('compilation: ([0-9.]+) s') }}, null))                          as init_engine_compile_s,
        max(iff(startswith(message, 'Available KV cache memory'), {{ log_num('([0-9.]+) GiB') }}, null))                       as kv_cache_gib,
        max(iff(startswith(message, 'Maximum concurrency'), {{ log_num(': ([0-9.]+)x') }}, null))                              as max_concurrency_x,
        -- Spark's regexp_extract yields "" (not null) for an init line without a version; keep that shape
        coalesce(max(iff(is_init, regexp_substr(message, $$\((v[0-9.]+)\)$$, 1, 1, 'e', 1), null)),
                 iff(sum(iff(is_init, 1, 0)) > 0, '', null))                                                               as vllm_version,
        max(iff({{ rx('message', 'Capturing CUDA graphs \\(FULL\\)') }}, 'FULL', null))                                     as g_full,
        max(iff({{ rx('message', 'Capturing CUDA graphs \\(PIECEWISE\\)') }}, 'PIECEWISE', null))                           as g_piece,
        coalesce(max(iff(startswith(message, '--- Starting Serverless Worker'), regexp_substr(message, $$Version ([0-9.]+)$$, 1, 1, 'e', 1), null)),
                 iff(sum(iff(startswith(message, '--- Starting Serverless Worker'), 1, 0)) > 0, '', null))                 as runpod_sdk_version,
        sum(iff(event_kind = 'progress', 1, 0))                                     as n_progress_lines,
        count(*)                                                                    as n_lines
    from segmented
    group by source_file, wk, boot_index
),

first_job as (
    select source_file, wk, boot_index, min(ts_utc) as t_first_job_seen
    from segmented
    where startswith(message, 'Jobs in queue')
    group by source_file, wk, boot_index
),

-- boot 0 = lines before any opener; a row only if it is a boot (carries a phase)
kept as (
    select b.*, f.t_first_job_seen
    from boots b
    left join first_job f on f.source_file = b.source_file and f.wk = b.wk and f.boot_index = b.boot_index
    where b.boot_index > 0
       or b.t_weights_loaded is not null or b.t_api_ready is not null or b.init_engine_s is not null or b.graph_capture_s is not null
)

select
    source_file, boot_index, worker_id, segmented_by, ts_format, vllm_version, runpod_sdk_version,
    -- the graph-capture mode is a configuration, and it — not the vLLM version — decides whether capture takes 5 s or 80 s:
    -- FULL graphs are captured per batch-size bucket for the whole model, PIECEWISE only around attention
    case when g_full is not null and g_piece is not null then 'FULL+PIECEWISE' else coalesce(g_full, g_piece) end   as graph_mode,
    t_start_vllm, t_api_ready,
    {{ secs_between('t_start_vllm', 't_weights_loaded') }}                          as start_to_weights_s,
    weights_load_s, model_gib, model_load_s, torch_compile_s,
    graph_capture_s, n_graph_passes, init_engine_s, init_engine_compile_s,
    {{ secs_between('t_start_vllm', 't_api_ready') }}                               as start_to_api_ready_s,
    {{ secs_between('t_api_ready', 't_sdk_started') }}                              as api_ready_to_sdk_s,
    iff(t_first_job_seen >= t_api_ready, {{ secs_between('t_api_ready', 't_first_job_seen') }}, null)   as api_ready_to_first_job_s,
    kv_cache_gib, max_concurrency_x,
    n_progress_lines, n_lines,
    sysdate()                                                                       as gold_built_at
from kept
order by source_file, boot_index
