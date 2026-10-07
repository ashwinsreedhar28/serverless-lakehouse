{{ config(schema='SILVER') }}
{#- $ per endpoint per hour from /v2/billing/serverless. Every poll re-reads the last 48 buckets, so the same bucket arrives
    many times; the latest poll wins (an in-progress bucket keeps growing until the hour closes). -#}
with polls as (select * from {{ ref('silver_runpod_polls') }}),
raw as (
    select b.source_sha256 as poll_id, r.value as rec
    from {{ source('bronze', 'bronze_runpod_polls') }} b, lateral flatten(input => b.doc:billing:records) r
    qualify row_number() over (partition by b.source_sha256, r.index order by b.ingested_at desc) = 1
),
typed as (
    select
        p.poll_seq, p.polled_at_utc,
        rec:serverlessId::string                                                as endpoint_id,
        convert_timezone('UTC', rec:startTime::timestamp_tz)::timestamp_ntz     as bucket_start_utc,
        convert_timezone('UTC', rec:endTime::timestamp_tz)::timestamp_ntz       as bucket_end_utc,
        rec:totalAmount::double                                                 as total_usd,
        rec:gpuAmount::double                                                   as gpu_usd,
        rec:cpuAmount::double                                                   as cpu_usd,
        rec:diskAmount::double                                                  as disk_usd
    from raw r
    join polls p on p.poll_id = r.poll_id
)
select *, sysdate() as silver_built_at
from typed
qualify row_number() over (partition by endpoint_id, bucket_start_utc order by poll_seq desc) = 1
