{{ config(schema='SILVER') }}
{#- Endpoint configuration as the API reports it, one row per poll × endpoint. `flashboot` is the authoritative setting the
    benchmark seeds could only infer. -#}
with polls as (select * from {{ ref('silver_runpod_polls') }}),
raw as (
    select b.source_sha256 as poll_id, e.value as ep
    from {{ source('bronze', 'bronze_runpod_polls') }} b, lateral flatten(input => b.doc:endpoints) e
    qualify row_number() over (partition by b.source_sha256, e.index order by b.ingested_at desc) = 1
)
select
    p.poll_id, p.poll_seq, p.polled_at_utc,
    ep:id::string                                   as endpoint_id,
    ep:name::string                                 as name,
    ep:type::string                                 as endpoint_type,
    ep:flashboot::string                            as flashboot,
    ep:gpu:pools                                    as gpu_pools,
    ep:gpu:count::int                               as gpu_count,
    ep:gpu:excludedTypes                            as gpu_excluded_types,
    ep:workers:min::int                             as workers_min,
    ep:workers:max::int                             as workers_max,
    ep:workers:idleTimeout::int                     as idle_timeout_s,
    ep:scaling:type::string                         as scaling_type,
    coalesce(ep:scaling:queueDelay::double, ep:scaling:requestCount::double)   as scaling_value,
    ep:timeout::number                              as request_timeout_ms,
    ep:image::string                                as image,
    ep:dataCenterIds                                as data_center_ids,
    ep:networkVolumes                               as network_volumes,
    convert_timezone('UTC', ep:createdAt::timestamp_tz)::timestamp_ntz   as created_at_utc,
    ep                                              as config_json,
    sysdate()                                       as silver_built_at
from raw r
join polls p on p.poll_id = r.poll_id
