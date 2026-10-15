{{ config(schema='SILVER') }}
{#- Runpod's own change log for each endpoint (GET /v2/serverless/{id}/releases): one row per endpoint × release version ×
    changed field. A release is written when a change needs a worker rollout (image, GPU selection, CUDA floor, data
    centers, disk, env); FlashBoot, workers and scaling changes do not write one. Releases are immutable, so every poll
    carries the same history and the latest copy of each version is kept. Values are kept only for the fields the
    dimension tracks (`column_name` not null); env and registry-auth diffs keep their field name only. Unset values are
    spelled as in silver_runpod_endpoint_config ('ALL' for CUDA floor / allowed CUDA / data centers, else null). -#}
with raw as (
    select b.source_sha256 as poll_id, b.ingested_at, b.doc:polled_at::timestamp_tz as polled_at,
           e.key::string as endpoint_id, e.value:pagination:hasNextPage::boolean as has_next_page, r.value as rel
    from {{ source('bronze', 'bronze_runpod_polls') }} b,
         lateral flatten(input => b.doc:releases) e,
         lateral flatten(input => e.value:releases) r
),
latest as (
    select * from raw
    qualify row_number() over (partition by endpoint_id, rel:version::int order by polled_at desc, ingested_at desc) = 1
),
diffs as (
    select
        l.endpoint_id,
        l.rel:version::int                                  as release_version,
        {{ to_utc('l.rel:createdAt::string') }}             as created_at_utc,
        l.rel:source::string                                as release_source,
        f.value:field::string                               as field,
        case f.value:field::string
            when 'gpuIds' then 'gpu_ids'
            when 'minCudaVersion' then 'min_cuda'
            when 'allowedCudaVersions' then 'allowed_cuda'
            when 'template.imageName' then 'image'
            when 'locations' then 'locations'
            when 'template.containerDiskInGb' then 'disk_gb'
        end                                                 as column_name,
        {{ variant_text('f.value:old') }}                   as old_raw,
        {{ variant_text('f.value:new') }}                   as new_raw,
        l.has_next_page, l.poll_id
    from latest l, lateral flatten(input => l.rel:diff, outer => true) f
)
select
    endpoint_id, release_version, created_at_utc, release_source, field, column_name,
    {%- for side in ['old', 'new'] %}
    case
        when column_name = 'gpu_ids'                      then nullif({{ gpu_ids_canonical(side ~ '_raw') }}, '')
        when column_name in ('allowed_cuda', 'locations') then {{ csv_sorted("coalesce(nullif(" ~ side ~ "_raw, ''), 'ALL')") }}
        when column_name = 'min_cuda'                     then coalesce(nullif({{ side }}_raw, ''), 'ALL')
        when column_name is not null                      then nullif({{ side }}_raw, '')
    end                                                     as {{ side }}_value,
    {%- endfor %}
    has_next_page                                           as history_truncated,
    poll_id                                                 as seen_in_poll_id,
    sysdate()                                               as silver_built_at
from diffs
