{#-
One worker-log line, timestamp parsed to UTC, payload classified. Port of lakehouse.silver.build_worker_log_events.

Three timestamp formats, one event table:
  console  "Wed Sep 23 2026 13:41:40 GMT-0400 (Eastern Daylight Time) <payload>"   — the console export's local time + offset
  iso      "2026-09-30T02:56:18.120314576Z <payload>"                               — the API's UTC (kept to the millisecond)
  pipe     "2026-09-23 14:50:51.989 | info | <worker_id> | <payload>"               — endpoint-logs export, laptop-local time
The endpoint-logs export also strips the "(Role pid=N)" prefix and the SDK's JSON wrapper, so the same vLLM / SDK lines
appear in two spellings; both land in the same event_kind.

Regexes are dollar-quoted (backslashes literal). Snowflake's REGEXP_LIKE anchors the whole string, so the `rx` macro uses
REGEXP_INSTR for Spark's search semantics; patterns do not end in `$` because `$$$` would close the literal early.
-#}

{%- set RX_CONSOLE = '^(Mon|Tue|Wed|Thu|Fri|Sat|Sun) ([A-Z][a-z]{2} \\d{2} \\d{4} \\d{2}:\\d{2}:\\d{2}) GMT([+-]\\d{4}) \\([^)]*\\) ?(.*)' %}
{%- set RX_ISO = '^(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3})\\d*Z ?(.*)' %}
{%- set RX_PIPE = '^(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}\\.\\d{3}) \\| (\\w+) \\| (\\w+) \\| ?(.*)' %}
{%- set RX_VLLM = '^\\((\\w+) pid=(\\d+)\\)\\s*(.*)' %}
{%- set RX_LEVEL = '^(INFO|WARNING|ERROR|DEBUG|CRITICAL)' %}
{%- set RX_VLLM_BARE = '^(INFO|WARNING|ERROR|DEBUG|CRITICAL)[: ]+\\d\\d-\\d\\d \\d\\d:\\d\\d:\\d\\d \\[' %}
{%- set RX_VLLM_PREFIX = '^(INFO|WARNING|ERROR|DEBUG|CRITICAL):?\\s*(\\d\\d-\\d\\d \\d\\d:\\d\\d:\\d\\d \\[[^]]+\\]\\s*)?' %}
{%- set RX_WRAPPER = '^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2},\\d+ (INFO|WARNING|ERROR) root:' %}
{%- set RX_WRAPPER_PREFIX = '^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2},\\d+ (INFO|WARNING|ERROR) root:\\s*' %}
{%- set RX_SDK_TEXT = '^(Jobs in (queue|progress): \\d+|Finished running generator\\.|Finished\\.|Running \\d+ fitness check|GPU binary test|Memory check|Disk space check|--- Starting Serverless Worker)' %}

with b as (
    {{ current_snapshot('bronze_worker_log_lines') }}
),

fmt as (
    select
        b.*,
        case
            when {{ rx('raw_line', RX_CONSOLE) }} then 'console'
            when {{ rx('raw_line', RX_ISO) }}     then 'iso'
            when {{ rx('raw_line', RX_PIPE) }}    then 'pipe'
            else 'none'
        end as ts_format
    from b
),

parsed as (
    select
        f.*,
        case ts_format
            when 'console' then convert_timezone('UTC', to_timestamp_tz(
                                    {{ rxg('raw_line', RX_CONSOLE, 2) }} || ' ' || {{ rxg('raw_line', RX_CONSOLE, 3) }},
                                    'MON DD YYYY HH24:MI:SS TZHTZM'))::timestamp_ntz
            when 'iso'     then to_timestamp_ntz({{ rxg('raw_line', RX_ISO, 1) }}, 'YYYY-MM-DD"T"HH24:MI:SS.FF3')
            when 'pipe'    then convert_timezone('{{ var("console_log_tz") }}', 'UTC',
                                    to_timestamp_ntz({{ rxg('raw_line', RX_PIPE, 1) }}, 'YYYY-MM-DD HH24:MI:SS.FF3'))
        end as ts_utc,
        iff(ts_format = 'pipe', {{ rxg('raw_line', RX_PIPE, 3) }}, null)            as worker_id,
        iff(ts_format = 'pipe', {{ rxg('raw_line', RX_PIPE, 2) }}, null)            as console_level,
        coalesce(case ts_format
            when 'console' then {{ rxg('raw_line', RX_CONSOLE, 4) }}
            when 'iso'     then {{ rxg('raw_line', RX_ISO, 2) }}
            when 'pipe'    then {{ rxg('raw_line', RX_PIPE, 4) }}
            else raw_line
        end, '') as payload
    from fmt f
),

classified as (
    select
        p.*,
        startswith(payload, '{"requestId"')                                         as is_sdk_json,
        {{ rx('payload', RX_SDK_TEXT) }}                                            as is_sdk_text,
        {{ rx('payload', RX_VLLM_BARE) }}                                           as is_vllm_bare,
        {{ rx('payload', RX_VLLM) }}                                                as has_role,
        try_parse_json(iff(startswith(payload, '{"requestId"'), payload, null))      as sdk
    from parsed p
),

kinds as (
    select
        c.*,
        case
            when is_sdk_json or is_sdk_text                                         then 'runpod_sdk'
            when has_role or is_vllm_bare                                           then 'vllm'
            when {{ rx('payload', '\\d+%\\|') }}
              or startswith(payload, 'Loading safetensors checkpoint shards:')       then 'progress'
            when {{ rx('payload', 'INFO httpx:') }}                                 then 'httpx'
            when {{ rx('payload', RX_WRAPPER) }}                                    then 'wrapper'
            when payload = ''                                                       then 'blank'
            else 'other'
        end as event_kind,
        coalesce(iff(has_role, {{ rxg('payload', RX_VLLM, 3) }}, payload), '')      as rest
    from classified c
)

select
    source_file, source_sha256, line_no, ts_utc, ts_format, worker_id, event_kind,
    iff(has_role, {{ rxg('payload', RX_VLLM, 1) }}, null)                           as process_role,
    iff(has_role, try_to_number({{ rxg('payload', RX_VLLM, 2) }})::int, null)       as pid,
    case
        when event_kind = 'vllm'    then {{ rxg('rest', RX_LEVEL, 1) }}
        when is_sdk_json            then sdk:level::string
        when event_kind = 'wrapper' then {{ rxg('payload', ' (INFO|WARNING|ERROR) root:', 1) }}
        else upper(console_level)
    end                                                                             as level,
    iff(is_sdk_json, sdk:requestId::string, null)                                   as request_id,
    case
        when event_kind = 'vllm'    then regexp_replace(rest, $${{ RX_VLLM_PREFIX }}$$, '')
        when is_sdk_json            then sdk:message::string
        when event_kind = 'wrapper' then regexp_replace(payload, $${{ RX_WRAPPER_PREFIX }}$$, '')
        else payload
    end                                                                             as message,
    payload,
    run_label                                                                       as bronze_run_label,
    sysdate()                                                                       as silver_built_at
from kinds
