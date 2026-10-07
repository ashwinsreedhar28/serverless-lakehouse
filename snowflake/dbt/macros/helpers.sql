{#-
Helpers shared by the silver and gold models. Each one names the Spark expression it stands in for.
-#}

{#- Spark `latest_per_file`: keep only the rows whose (source_file, source_sha256) the landing manifest names as current,
    and exactly one ingest of that pair (the latest, run_label as tie-break) in case --force appended it twice.
    LANDING.MANIFEST_SNAPSHOT has one row per file × expected table, written by lakehouse.sf.bronze on every run. -#}
{% macro current_snapshot(bronze_table) -%}
    select b.*
    from {{ source('bronze', bronze_table) }} b
    join {{ source('landing', 'manifest_snapshot') }} m
      on m.source_file = b.source_file and m.source_sha256 = b.source_sha256 and m.expected_table = '{{ bronze_table }}'
    qualify dense_rank() over (partition by b.source_file, b.source_sha256 order by b.ingested_at desc, b.run_label desc) = 1
{%- endmacro %}

{#- Spark `canonical_model`: one name per model across sources. -#}
{% macro canonical_model(col) -%}
    case lower({{ col }})
        when 'qwen/qwen3-8b' then 'Qwen3-8B'
        when 'qwen/qwen3-32b-awq' then 'Qwen3-32B-AWQ'
        when 'qwen/qwen2.5-7b' then 'Qwen2.5-7B'
        when 'qwen2.5-7b' then 'Qwen2.5-7B'
        when 'qwen/qwen2.5-0.5b' then 'Qwen2.5-0.5B'
        when 'qwen2.5-0.5b' then 'Qwen2.5-0.5B'
        else {{ col }}
    end
{%- endmacro %}

{#- Spark `endpoint_from_url`: the endpoint id from a queue URL (/v2/<id>/…) or a load-balancer URL (https://<id>.api.runpod.ai). -#}
{% macro endpoint_from_url(col) -%}
    coalesce(
        regexp_substr({{ col }}, $$/v2/([a-z0-9]+)(/|$)$$, 1, 1, 'e', 1),
        regexp_substr({{ col }}, $$https://([a-z0-9]+)\.api\.runpod\.ai$$, 1, 1, 'e', 1)
    )
{%- endmacro %}

{#- Pulse writes empty strings for missing values; Spark's readers turned most of them into null already. -#}
{% macro nz(col) -%}
    nullif({{ col }}, '')
{%- endmacro %}

{#- Spark `percentile_approx(col, q)` returns an observed value: the one at 1-based rank ceil(q·n). PERCENTILE_DISC
    returns the first value whose cumulative distribution ≥ q, which is the same element. No interpolation either way. -#}
{% macro pct(col, q) -%}
    percentile_disc({{ q }}) within group (order by {{ col }})
{%- endmacro %}

{#- Spark `col.cast("int")` on a boolean: true→1, false→0, null→null (so SUM skips it, unlike IFF(x,1,0)). -#}
{% macro b2i(col) -%}
    iff({{ col }} is null, null, iff({{ col }}, 1, 0))
{%- endmacro %}

{#- Spark `rlike`: a regex *search* (Snowflake's REGEXP_LIKE anchors the whole string, so use REGEXP_INSTR instead).
    Patterns are dollar-quoted, so backslashes are literal. -#}
{% macro rx(col, pattern) -%}
    (regexp_instr({{ col }}, $${{ pattern }}$$) > 0)
{%- endmacro %}

{#- Spark `regexp_extract(col, pattern, n)`; null instead of "" when there is no match. -#}
{% macro rxg(col, pattern, n) -%}
    regexp_substr({{ col }}, $${{ pattern }}$$, 1, 1, 'e', {{ n }})
{%- endmacro %}

{#- An ISO-8601 string with an offset → the UTC instant as TIMESTAMP_NTZ (Spark TimestampType with session zone UTC). -#}
{% macro to_utc(col) -%}
    convert_timezone('UTC', to_timestamp_tz({{ col }}))::timestamp_ntz
{%- endmacro %}

{#- A Unix epoch in seconds as a double → TIMESTAMP_NTZ at microsecond precision (Spark `to_timestamp(double)` truncates). -#}
{% macro epoch_s_to_ts(col) -%}
    to_timestamp_ntz(trunc(({{ col }})::double * 1000000)::number(38, 0), 6)
{%- endmacro %}

{#- Seconds between two timestamps as a double (Spark `b.cast("double") - a.cast("double")`). -#}
{% macro secs_between(a, b) -%}
    (date_part(epoch_microsecond, {{ b }}) - date_part(epoch_microsecond, {{ a }})) / 1000000.0
{%- endmacro %}

{#- A VARIANT scalar that the source may have written as a string or as something else: string as-is, anything else as JSON text. -#}
{% macro variant_text(expr) -%}
    iff({{ expr }} is null or is_null_value({{ expr }}), null, iff(is_varchar({{ expr }}), ({{ expr }})::string, to_json({{ expr }})))
{%- endmacro %}

{#- Spark `regexp_extract(message, pattern, 1).cast("double")` in gold_worker_boot_phases: a number out of a vLLM log line. -#}
{% macro log_num(pattern) -%}
    try_to_double(regexp_substr(message, $${{ pattern }}$$, 1, 1, 'e', 1))
{%- endmacro %}
