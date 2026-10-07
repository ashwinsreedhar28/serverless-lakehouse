{#-
One request-rate run of a load sweep, typed: the summary / trace / args / server_latency JSON strings bronze kept,
exploded into columns. Port of lakehouse.silver.build_sweep_summaries.
-#}

with b as (
    {{ current_snapshot('bronze_sweep_runs') }}
),

parsed as (
    select
        b.*,
        try_parse_json(summary_json)            as s,
        try_parse_json(trace_json)              as t,
        try_parse_json(args_json)               as a,
        try_parse_json(server_latency_json)     as sl
    from b
)

select
    system,
    model                                                       as served_model,
    {{ endpoint_from_url('base_url') }}                         as endpoint_id,
    iff(contains(base_url, '/v2/'), 'queue', 'load_balancer')   as endpoint_mode,
    run_index::int                                              as run_index,
    -- null request_rate is the unbounded ("inf") run: every request sent at t=0
    coalesce(request_rate, 'inf'::double)                       as request_rate,
    request_rate is null                                        as is_unbounded,
    a:max_concurrency::int                                      as max_concurrency,
    a:client_procs::int                                         as client_procs,
    wall_s,
    s:num_requests::number                                      as num_requests,
    s:completed::number                                         as completed,
    s:failed::number                                            as failed,
    s:duration_s::double                                        as duration_s,
    s:requests_per_s::double                                    as requests_per_s,
    s:throughput_tok_s::double                                  as output_tok_s,
    s:total_throughput_tok_s::double                            as total_tok_s,
    {%- for m in ['ttft_ms', 'tpot_ms', 'e2e_ms'] %}
    {%- for k in ['mean', 'p50', 'p90', 'p99'] %}
    s:{{ m }}:{{ k }}::double                                   as {{ m }}_{{ k }},
    {%- endfor %}
    {%- endfor %}
    s:prompt_tokens::number                                     as prompt_tokens,
    s:output_tokens::number                                     as output_tokens,
    t:n::number                                                 as trace_n,
    t:prompt_mean::double                                       as trace_prompt_mean,
    t:output_mean::double                                       as trace_output_mean,
    t:source::string                                            as trace_source,
    sl:ttft_ms_mean::double                                     as server_ttft_ms_mean,
    sl:tpot_ms_mean::double                                     as server_tpot_ms_mean,
    sl:e2e_ms_mean::double                                      as server_e2e_ms_mean,
    n_records,
    source_file, source_sha256,
    run_label                                                   as bronze_run_label,
    sysdate()                                                   as silver_built_at
from parsed
