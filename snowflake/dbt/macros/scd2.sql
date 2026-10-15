{#-
Helpers for the endpoint-config history (dim_runpod_endpoint, dim_runpod_endpoint_release, snap_runpod_endpoint_config).
-#}

{#- The columns a new Type 2 version starts on. workers.min/max are deliberately absent: the campaign flips max 0→1→0
    inside one cell (minutes), faster than any poll, so they are carried as current-value (Type 1) columns instead. -#}
{% macro endpoint_tracked_cols() -%}
    {{ return(['gpu_ids', 'min_cuda', 'allowed_cuda', 'image', 'locations', 'disk_gb',
               'flashboot', 'idle_timeout_s', 'scaling_type', 'scaling_value', 'request_timeout_ms', 'network_volumes']) }}
{%- endmacro %}

{#- The subset Runpod writes a release for (GET /v2/serverless/{id}/releases), so it has an exact change time. -#}
{% macro release_tracked_cols() -%}
    {{ return(['gpu_ids', 'min_cuda', 'allowed_cuda', 'image', 'locations', 'disk_gb']) }}
{%- endmacro %}

{#- Null-safe md5 over a list of columns (Snowflake's CONCAT_WS returns null if any argument is null). -#}
{% macro scd2_hash(cols) -%}
    md5(concat_ws('|'{% for c in cols %}, coalesce(({{ c }})::string, '<null>'){% endfor %}))
{%- endmacro %}

{#- A comma-separated list with its elements sorted, so two spellings of the same set compare equal. -#}
{% macro csv_sorted(s) -%}
    array_to_string(array_sort(split({{ s }}, ',')), ',')
{%- endmacro %}

{#- An API array as the releases spell it: sorted, comma-joined, and 'ALL' when empty. -#}
{% macro list_or_all(arr) -%}
    iff(array_size(coalesce(({{ arr }})::array, array_construct())) = 0, 'ALL', array_to_string(array_sort(({{ arr }})::array), ','))
{%- endmacro %}

{#- The GPU selection in the releases' `gpuIds` spelling: pools, then excluded types prefixed with '-', e.g.
    "AMPERE_80,-NVIDIA A100-SXM4-80GB". Both groups sorted. -#}
{% macro gpu_ids_from_api(pools, excluded) -%}
    array_to_string(array_cat(
        array_sort(coalesce(({{ pools }})::array, array_construct())),
        array_sort(transform(coalesce(({{ excluded }})::array, array_construct()), x -> '-' || x::string))), ',')
{%- endmacro %}

{#- The same canonical order for a `gpuIds` string out of a release diff. -#}
{% macro gpu_ids_canonical(s) -%}
    array_to_string(array_cat(
        array_sort(filter(split({{ s }}, ','), x -> not startswith(x::string, '-'))),
        array_sort(filter(split({{ s }}, ','), x -> startswith(x::string, '-')))), ',')
{%- endmacro %}
