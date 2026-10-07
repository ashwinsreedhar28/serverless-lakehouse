{#-
One request of a sweep run, with ttft / e2e / tpot derived from the client's arrival, first-token and finish clocks.
Port of lakehouse.silver.build_sweep_requests.
-#}

with b as (
    {{ current_snapshot('bronze_sweep_records') }}
)

select
    system,
    run_index::int                                              as run_index,
    coalesce(request_rate, 'inf'::double)                       as request_rate,
    request_id,
    arrival_s - min(arrival_s) over (partition by source_file, run_index)   as arrival_offset_s,
    prompt_tokens,
    output_tokens,
    success,
    error,
    case when success then (first_token_s - arrival_s) * 1000 end                          as ttft_ms,
    case when success then (finish_s - arrival_s) * 1000 end                               as e2e_ms,
    case when success and output_tokens > 1
         then (finish_s - first_token_s) * 1000 / (output_tokens - 1) end                  as tpot_ms,
    source_file, source_sha256,
    run_label                                                   as bronze_run_label,
    sysdate()                                                   as silver_built_at
from b
