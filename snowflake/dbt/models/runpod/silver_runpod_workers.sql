{{ config(schema='SILVER') }}
{#- One row per poll × endpoint × *active* worker. Scaled-down workers are not returned by the API, so a worker's life is
    the run of polls in which it appears (silver_runpod_worker_events diffs consecutive polls). -#}
with polls as (select * from {{ ref('silver_runpod_polls') }}),
raw as (
    select b.source_sha256 as poll_id, w.key as endpoint_id, w.value as resp
    from {{ source('bronze', 'bronze_runpod_polls') }} b, lateral flatten(input => b.doc:workers) w
    qualify row_number() over (partition by b.source_sha256, w.key order by b.ingested_at desc) = 1
),
workers as (
    select r.poll_id, r.endpoint_id, r.resp:endpointVersion::int as endpoint_version, x.value as wk
    from raw r, lateral flatten(input => r.resp:workers) x
)
select
    p.poll_id, p.poll_seq, p.polled_at_utc,
    w.endpoint_id,
    wk:id::string                                   as worker_id,
    wk:status::string                               as status,
    wk:gpuTypeId::string                            as gpu_type_id,
    wk:dataCenterId::string                         as data_center_id,
    convert_timezone('UTC', wk:startedAt::timestamp_tz)::timestamp_ntz   as started_at_utc,
    wk:uptimeSeconds::number                        as uptime_s,
    wk:image::string                                as image,
    wk:version::int                                 as config_version,
    w.endpoint_version,
    wk:isStale::boolean                             as is_stale,
    wk:gpuCount::int                                as gpu_count,
    sysdate()                                       as silver_built_at
from workers w
join polls p on p.poll_id = w.poll_id
