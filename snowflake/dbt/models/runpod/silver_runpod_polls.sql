{{ config(schema='SILVER') }}
{#- One row per API snapshot: when it was taken and what it saw. The sequence number orders polls for the worker diff. -#}
select
    source_sha256                                                   as poll_id,
    doc:polled_at::timestamp_tz                                     as polled_at_tz,
    convert_timezone('UTC', doc:polled_at::timestamp_tz)::timestamp_ntz   as polled_at_utc,
    row_number() over (order by doc:polled_at::timestamp_tz, source_sha256)  as poll_seq,
    array_size(doc:endpoints)                                       as n_endpoints,
    doc:billing:metadata:recordCount::number                        as n_billing_records,
    array_size(doc:jobs)                                            as n_job_lookups,
    source_file, ingested_at, run_label                             as bronze_run_label,
    sysdate()                                                       as silver_built_at
from {{ source('bronze', 'bronze_runpod_polls') }}
-- the same document loaded twice (FORCE) counts once
qualify row_number() over (partition by source_sha256 order by ingested_at desc) = 1
