-- Spark: silver.assert_snapshot_in_bronze / tests test_silver_refuses_when_bronze_lacks_the_current_version and
-- test_partial_multi_table_ingest_is_refused_then_repaired.
-- Every (file, sha, table) the landing manifest implies must be complete in bronze: present in the data table, or recorded
-- in the ingest ledger (a zero-row file has no data rows but a logged append). Checked per *expected* table, so a run that
-- died between a sweep's summary append and its records append fails here instead of yielding a quietly thinner silver.
with present as (
    select table_name, source_file, source_sha256 from {{ source('bronze', 'bronze_ingest_log') }}
    {%- for t in ['bronze_raw_json', 'bronze_coldstart_series', 'bronze_coldstart_runs', 'bronze_sweep_runs', 'bronze_sweep_records',
                  'bronze_worker_log_lines', 'bronze_pulse_coldstart_requests', 'bronze_pulse_throughput_requests',
                  'bronze_pulse_quality_requests', 'bronze_pulse_quality_batches'] %}
    union
    select distinct '{{ t }}', source_file, source_sha256 from {{ source('bronze', t) }}
    {%- endfor %}
)
select m.source_file, m.source_sha256, m.expected_table
from {{ source('landing', 'manifest_snapshot') }} m
left join present p
  on p.table_name = m.expected_table and p.source_file = m.source_file and p.source_sha256 = m.source_sha256
where p.source_file is null
