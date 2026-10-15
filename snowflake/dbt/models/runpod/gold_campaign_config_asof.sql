{{ config(schema='GOLD') }}
{#- Every completed campaign cold start (kind = 'cold' and ok: the same set the campaign gold tables count), joined
    point-in-time (endpoint_id + request time inside [valid_from, valid_to)) to both config histories, and scored
    against what the cell actually asked Runpod for:
      - GPU: seeds/campaign_gpu_pins.csv, the selection tools/campaign.py PATCHes for each GPU model (pool minus the
        pool's other types, per Runpod's published pool list) — independent of either history
      - FlashBoot: the cell's design (seed row). Only the poll history has FlashBoot: Runpod writes no release for it.
    The campaign re-points three endpoints every cell, minutes before each cold start, so this is the hard case for a
    sampled history. -#}
with cold as (
    select series_label, endpoint_id, run_index, source_file, request_ts_utc,
           gpu_model as design_gpu_model, flashboot as design_flashboot
    from {{ ref('silver_campaign_requests') }}
    where kind = 'cold' and ok and campaign_kind = 'campaign'
),
pit as (
    select c.*,
           r.gpu_ids            as release_gpu_ids,
           r.version_no         as release_version_no,
           r.valid_from_utc     as release_valid_from_utc,
           p.gpu_ids            as poll_gpu_ids,
           p.flashboot          as poll_flashboot,
           p.version_no         as poll_version_no,
           p.valid_from_utc     as poll_valid_from_utc,
           p.changed_after_utc  as poll_changed_after_utc
    from cold c
    left join {{ ref('dim_runpod_endpoint_release') }} r
      on r.endpoint_id = c.endpoint_id
     and c.request_ts_utc >= r.valid_from_utc and c.request_ts_utc < coalesce(r.valid_to_utc, '9999-12-31'::timestamp_ntz)
    left join {{ ref('dim_runpod_endpoint') }} p
      on p.endpoint_id = c.endpoint_id
     and c.request_ts_utc >= p.valid_from_utc and c.request_ts_utc < coalesce(p.valid_to_utc, '9999-12-31'::timestamp_ntz)
)
select
    p.*,
    k.gpu_ids                                                                      as expected_gpu_ids,
    equal_null(p.release_gpu_ids, k.gpu_ids)                                       as release_gpu_agrees,
    equal_null(p.poll_gpu_ids, k.gpu_ids)                                          as poll_gpu_agrees,
    case lower(p.design_flashboot)
        when 'on'  then coalesce(p.poll_flashboot in ('FLASHBOOT', 'PRIORITY_FLASHBOOT'), false)
        when 'off' then coalesce(p.poll_flashboot = 'OFF', false)
    end                                                                            as poll_flashboot_agrees,
    datediff('second', p.release_valid_from_utc, p.request_ts_utc)                 as s_since_release_version,
    sysdate()                                                                      as gold_built_at
from pit p
left join {{ ref('campaign_gpu_pins') }} k on k.gpu_model = p.design_gpu_model
