{#- Event-level projection for the dashboard's dot plot: every successful cold request, one row. Port of lakehouse.gold.coldstart_events. -#}

select
    source, engine, model,
    coalesce(gpu_model, 'not captured')                 as gpu_model,
    gpu_tier, weights_mode, flashboot, host_state, series_label, endpoint_id, run_index,
    request_ts_utc, delay_ms, exec_ms, worker_id, is_flashboot_hit, flashboot_resume_recorded,
    est_cost_usd, source_file,
    sysdate()                                           as gold_built_at
from {{ ref('silver_coldstart_requests') }}
where ok and kind = 'cold'
order by engine, weights_mode, delay_ms
