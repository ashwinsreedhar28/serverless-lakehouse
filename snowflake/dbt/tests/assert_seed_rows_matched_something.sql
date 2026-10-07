-- Spark: silver.check_seeds_matched. A seed row that names an endpoint / series present in the data but matches no request is
-- a broken key, not a missing fact: the A40 override would silently fall back to the typed label and put a 177 s A40 boot
-- back into the RTX 4090 comparison. Only noted (not failed) when the endpoint / series is absent from this snapshot.
with req as (select * from {{ ref('silver_coldstart_requests') }}),
ov_unmatched as (
    select 'coldstart_request_overrides' as seed, ov.endpoint_id as key1, ov.ts_utc as key2
    from {{ ref('dim_coldstart_request_overrides') }} ov
    left join req r on r.endpoint_id = ov.endpoint_id and r.request_ts_utc = {{ to_utc('ov.ts_utc') }} and r.gpu_label_override_note is not null
    where r.endpoint_id is null
      and ov.endpoint_id in (select distinct endpoint_id from req)
),
notes_unmatched as (
    select 'coldstart_run_notes', n.series_label, n.run_index::string
    from {{ ref('dim_coldstart_run_notes') }} n
    left join req r on r.series_label = n.series_label and r.run_index = n.run_index
    where r.series_label is null
      and n.series_label in (select distinct series_label from req where series_label is not null)
)
select * from ov_unmatched
union all
select * from notes_unmatched
