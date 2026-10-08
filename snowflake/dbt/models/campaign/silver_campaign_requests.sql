{{ config(schema='SILVER', tags=['campaign']) }}
{#- Every request of a campaign cell or the load generator, with the cell's design (GPU, FlashBoot, image) from the seed row
    the campaign driver wrote, the gap since the previous request on the same endpoint, and the UTC time-of-day slot. -#}
with flags as (
    -- The driver records a cold and a warm request per run. When the cold request never became a job (409 ENDPOINT_PAUSED
    -- from a max-workers change still propagating; /runsync handing back IN_QUEUE), the warm request that followed is the one
    -- that waited for a fresh worker — and the script itself marks it `cold: true`. That request is the cell's cold start.
    select source_file, source_sha256, run_index::int as run_index,
           coalesce(try_parse_json(cold_json):ok::boolean, false)      as cold_ok,
           coalesce(try_parse_json(warm_json):cold::boolean, false)    as warm_was_cold
    from ({{ current_snapshot('bronze_coldstart_runs') }})
),
req as (
    select
        r.* exclude (silver_built_at, kind, is_flashboot_hit),
        iff(r.kind = 'warm' and f.warm_was_cold and not f.cold_ok, 'cold', r.kind)                 as kind,
        r.kind                                                                                       as phase_recorded,
        -- a cold request lost on the client side (no job was ever placed) is not a placement failure of the tier
        r.kind = 'cold' and not r.ok and (coalesce(r.error, '') ilike '%ENDPOINT_PAUSED%' or coalesce(r.error, '') ilike '%IN_QUEUE%')
                                                                                                     as client_error,
        s.notes as series_notes
    from {{ ref('silver_coldstart_requests') }} r
    join {{ ref('dim_coldstart_series') }} s on s.series_label = r.series_label
    left join flags f on f.source_file = r.source_file and f.source_sha256 = r.source_sha256 and f.run_index = r.run_index
    where s.notes like 'campaign cell%' or r.series_label like 'loadgen%'
),
phases as (
    select series_label, run_index, source_file,
           max(iff(name = 'schedule_pull_create', seconds, null))  as placement_pull_create_s,
           max(iff(name = 'engine_boot', seconds, null))           as engine_boot_s,
           max(iff(name = 'download_after_spawn', seconds, null))  as download_after_spawn_s,
           max(iff(name = 'submit_to_first_job', seconds, null))   as submit_to_first_job_s
    from {{ ref('silver_coldstart_phases') }}
    where kind = 'phase'
    group by 1, 2, 3
)
select
    r.*,
    case when r.kind = 'cold' then (r.ok and r.delay_ms < {{ var('flashboot_hit_ms') }}) end       as is_flashboot_hit,
    iff(r.series_label like 'loadgen%', 'loadgen', 'campaign')                      as campaign_kind,
    p.placement_pull_create_s, p.engine_boot_s, p.download_after_spawn_s, p.submit_to_first_job_s,
    datediff('second', lag(r.request_ts_utc) over (partition by r.endpoint_id order by r.request_ts_utc), r.request_ts_utc)   as gap_since_prev_request_s,
    hour(r.request_ts_utc)                                                          as hour_utc,
    case when hour(r.request_ts_utc) < 6 then '00-06' when hour(r.request_ts_utc) < 12 then '06-12'
         when hour(r.request_ts_utc) < 18 then '12-18' else '18-24' end            as slot_utc,
    sysdate()                                                                       as silver_built_at
from req r
left join phases p on p.series_label = r.series_label and p.run_index = r.run_index and p.source_file = r.source_file
