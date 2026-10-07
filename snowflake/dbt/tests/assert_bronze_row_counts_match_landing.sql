-- Spark: lakehouse.verify (`make verify`). For the current snapshot, each bronze table holds exactly the rows the landed
-- file contains, as counted by plain Python when the manifest snapshot was written (not by Snowflake). A 2× count means
-- the file was appended twice; the dedupe in current_snapshot() hides that from silver, so it is still flagged here.
with actual as (
    {%- for t in ['bronze_raw_json', 'bronze_coldstart_series', 'bronze_coldstart_runs', 'bronze_sweep_runs', 'bronze_sweep_records',
                  'bronze_worker_log_lines', 'bronze_pulse_coldstart_requests', 'bronze_pulse_throughput_requests',
                  'bronze_pulse_quality_requests', 'bronze_pulse_quality_batches'] %}
    {%- if not loop.first %}
    union all
    {%- endif %}
    select '{{ t }}' as table_name, source_file, source_sha256, ingested_at, run_label, count(*) as n
    from {{ source('bronze', t) }} group by 1, 2, 3, 4, 5
    {%- endfor %}
),
-- one ingest per (file, sha): the one current_snapshot() selects
chosen as (
    select * from actual
    qualify dense_rank() over (partition by table_name, source_file, source_sha256 order by ingested_at desc, run_label desc) = 1
)
select m.expected_table, m.source_file, m.source_sha256, m.expected_rows, coalesce(c.n, 0) as found_rows
from {{ source('landing', 'manifest_snapshot') }} m
left join chosen c
  on c.table_name = m.expected_table and c.source_file = m.source_file and c.source_sha256 = m.source_sha256
where coalesce(c.n, 0) != m.expected_rows
