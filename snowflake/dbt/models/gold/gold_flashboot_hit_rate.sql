{#-
Fast-cold-response rate, a *proxy* for FlashBoot: successful cold-labelled requests answered under the threshold.
Denominator = successful cold requests (failures excluded). It cannot tell a FlashBoot resume from a worker that was
still warm; Runpod's own accounting is not in the data. n_cold_failed sits beside the rate so a 100 % on one boot reads
as 1-of-1-after-N-failures, not as a clean record. Port of lakehouse.gold.flashboot_hit_rate.
-#}

with cold as (
    select
        *,
        ok and coalesce(is_flashboot_hit, false)                            as hit
    from {{ ref('silver_coldstart_requests') }}
    where kind = 'cold'
)

select
    engine, model, endpoint_id,
    flashboot                                                               as flashboot_setting,
    sum({{ b2i('ok') }})                                                    as n_cold,
    sum({{ b2i('(not ok)') }})                                              as n_cold_failed,
    sum({{ b2i('hit') }})                                                   as n_hits,
    sum({{ b2i('coalesce(flashboot_resume_recorded, false)') }})            as n_resume_recorded,
    {{ pct('iff(hit, delay_ms, null)', 0.5) }}                              as hit_delay_ms_p50,
    {{ pct('iff(ok and not hit, delay_ms, null)', 0.5) }}                   as miss_delay_ms_p50,
    min(request_ts_utc)                                                     as first_request_utc,
    max(request_ts_utc)                                                     as last_request_utc,
    iff(n_cold > 0, round(n_hits::double / n_cold, 3), null)                as hit_rate,
    {{ var('flashboot_hit_ms') }}                                           as hit_threshold_ms,
    sysdate()                                                               as gold_built_at
from cold
group by engine, model, endpoint_id, flashboot
order by engine, model, endpoint_id
