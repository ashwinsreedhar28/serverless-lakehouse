{{ config(severity='warn', tags=['runpod']) }}
{#- dim_runpod_endpoint_release is rebuilt from diffs; this checks the rebuild against ground truth. For every poll ×
    endpoint, the release version valid at the poll's time must hold exactly the release-tracked values the poll saw.
    A miss means a diff was lost (paginated history, an unmapped field) or the rebuild rule is wrong. Warn, not error:
    a poll landing within the instant a release is being applied could legitimately straddle it. -#}
{%- set cols = release_tracked_cols() %}
select o.endpoint_id, o.poll_id, o.polled_at_utc, r.version_no, r.valid_from_utc,
       {% for c in cols %}o.{{ c }} as seen_{{ c }}, r.{{ c }} as rebuilt_{{ c }}{{ ',' if not loop.last }}
       {% endfor %}
from {{ ref('silver_runpod_endpoint_config') }} o
left join {{ ref('dim_runpod_endpoint_release') }} r
  on r.endpoint_id = o.endpoint_id
 and o.polled_at_utc >= r.valid_from_utc
 and o.polled_at_utc < coalesce(r.valid_to_utc, '9999-12-31'::timestamp_ntz)
where r.endpoint_id is null
   {% for c in cols %}or not equal_null(o.{{ c }}, r.{{ c }})
   {% endfor %}
