{#- ttft / e2e / throughput per system × request rate, with per-request percentiles where records were saved. Port of lakehouse.gold.sweep_latency. -#}

with rec as (
    select
        source_file, run_index,
        {{ pct('ttft_ms', 0.5) }}                                   as rec_ttft_ms_p50,
        {{ pct('ttft_ms', 0.99) }}                                  as rec_ttft_ms_p99,
        {{ pct('e2e_ms', 0.99) }}                                   as rec_e2e_ms_p99,
        count(*)                                                    as rec_n_ok
    from {{ ref('silver_sweep_requests') }}
    where success
    group by source_file, run_index
)

select
    s.system, s.endpoint_id, s.endpoint_mode, s.served_model, s.request_rate, s.is_unbounded,
    s.max_concurrency, s.num_requests, s.completed, s.failed, s.duration_s, s.requests_per_s,
    s.output_tok_s, s.total_tok_s, s.ttft_ms_p50, s.ttft_ms_p99, s.tpot_ms_p50, s.tpot_ms_p99,
    s.e2e_ms_p50, s.e2e_ms_p99, s.server_ttft_ms_mean, s.server_e2e_ms_mean,
    r.rec_n_ok, r.rec_ttft_ms_p50, r.rec_ttft_ms_p99, r.rec_e2e_ms_p99, s.source_file,
    sysdate()                                                       as gold_built_at
from {{ ref('silver_sweep_summaries') }} s
left join rec r on r.source_file = s.source_file and r.run_index = s.run_index
order by s.system, s.request_rate
