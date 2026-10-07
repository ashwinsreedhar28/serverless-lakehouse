{#- One scoring batch (Pulse quality_batches.csv), typed. Port of lakehouse.silver.build_scoring_batches. -#}

with b as (
    {{ current_snapshot('bronze_pulse_quality_batches') }}
)

select
    batch_id,
    {{ to_utc('ts_utc') }}                          as batch_ts_utc,
    backend,
    {{ canonical_model('model') }}                  as model,
    model                                           as model_raw,
    {{ nz('label') }}                               as label,
    host,
    {{ nz('gpu') }}                                 as gpu_model,
    {{ nz('worker_id') }}                           as worker_id,
    try_to_number(concurrency)::int                 as concurrency,
    try_to_number(n)::int                           as n,
    try_to_number(ok)::int                          as n_ok,
    try_to_number(parse_ok)::int                    as n_parse_ok,
    try_to_number(wall_ms)                          as wall_ms,
    {{ nz('served_model') }}                        as served_model,
    {{ nz('workers_before') }}                      as workers_before_json,
    price_unit,
    try_to_double({{ nz('rate_in') }})              as rate_in_usd_per_m,
    try_to_double({{ nz('rate_out') }})             as rate_out_usd_per_m,
    try_to_double({{ nz('rate_hr') }})              as rate_usd_per_hr,
    rate_source,
    try_to_double({{ nz('est_cost_usd') }})         as est_cost_usd,
    fixture_sha,
    {{ nz('note') }}                                as note,
    source_file, source_sha256,
    run_label                                       as bronze_run_label,
    sysdate()                                       as silver_built_at
from b
