{{ config(schema='SILVER') }}
{#- The config each poll saw, one row per poll × endpoint, in canonical text: the same spelling Runpod's /releases diffs
    use (gpuIds "AMPERE_80,-NVIDIA A100-SXM4-80GB", 'ALL' for an empty list), so the poll-built and the release-built
    histories compare column for column. `config_hash` covers endpoint_tracked_cols(). -#}
with c as (
    select
        e.poll_id, e.poll_seq, e.polled_at_utc, e.endpoint_id, e.name,
        {{ gpu_ids_from_api('e.gpu_pools', 'e.gpu_excluded_types') }}                  as gpu_ids,
        coalesce(nullif(e.config_json:gpu:minCudaVersion::string, ''), 'ALL')          as min_cuda,
        {{ list_or_all('e.config_json:gpu:allowedCudaVersions') }}                     as allowed_cuda,
        e.image,
        {{ list_or_all('e.data_center_ids') }}                                         as locations,
        e.config_json:disk::string                                                     as disk_gb,
        e.flashboot, e.idle_timeout_s, e.scaling_type, e.scaling_value, e.request_timeout_ms,
        to_json(coalesce(e.network_volumes, array_construct()))                        as network_volumes,
        e.workers_min, e.workers_max
    from {{ ref('silver_runpod_endpoints') }} e
)
select c.*, {{ scd2_hash(endpoint_tracked_cols()) }} as config_hash, sysdate() as silver_built_at
from c
