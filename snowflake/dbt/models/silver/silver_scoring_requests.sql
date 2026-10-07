{#- One scored article (Pulse quality.py), typed. Port of lakehouse.silver.build_scoring_requests. -#}

with b as (
    {{ current_snapshot('bronze_pulse_quality_requests') }}
)

select
    {{ to_utc('ts_utc') }}                          as request_ts_utc,
    backend,
    {{ canonical_model('model') }}                  as model,
    model                                           as model_raw,
    {{ nz('label') }}                               as label,
    host,
    {{ nz('gpu') }}                                 as gpu_model,
    batch_id,
    try_to_number(concurrency)::int                 as concurrency,
    try_to_number(article_id)                       as article_id,
    domain,
    try_to_number(wall_ms)                          as wall_ms,
    try_to_number(prompt_tokens)                    as prompt_tokens,
    try_to_number(completion_tokens)                as completion_tokens,
    {{ nz('finish_reason') }}                       as finish_reason,
    try_to_number(score)::int                       as score,
    {{ nz('reason') }}                              as reason,
    parse_ok = '1'                                  as parse_ok,
    {{ nz('error') }}                               as error,
    price_unit,
    try_to_double({{ nz('rate_in') }})              as rate_in_usd_per_m,
    try_to_double({{ nz('rate_out') }})             as rate_out_usd_per_m,
    try_to_double({{ nz('rate_hr') }})              as rate_usd_per_hr,
    rate_source,
    try_to_double({{ nz('est_cost_usd') }})         as est_cost_usd,
    fixture_sha,
    extra                                           as extra_json,
    source_file, source_sha256,
    run_label                                       as bronze_run_label,
    sysdate()                                       as silver_built_at
from b
