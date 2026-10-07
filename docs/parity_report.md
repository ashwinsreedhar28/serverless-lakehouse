# Parity: Snowflake gold vs Spark gold

Spark side: `space/data/gold.json` (built 2026-10-03 00:07 UTC). Snowflake side: `LAKEHOUSE.GOLD` read 2026-10-07 22:06 UTC. Floats compared within 1e-06 relative; timestamps at second precision; NaN ≡ null; arrays element-wise.

**8 of 8 tables match.**

| table | Spark rows | Snowflake rows | result |
|---|---|---|---|
| gold_coldstart_by_gpu_image | 32 | 32 | MATCH |
| gold_flashboot_hit_rate | 15 | 15 | MATCH |
| gold_engine_comparison | 12 | 12 | MATCH |
| gold_worker_boot_phases | 18 | 18 | MATCH |
| gold_cost_per_job | 16 | 16 | MATCH |
| gold_scoring_cost_per_batch | 14 | 14 | MATCH |
| gold_sweep_latency | 38 | 38 | MATCH |
| gold_coldstart_events | 47 | 47 | MATCH |

### gold_coldstart_by_gpu_image

- rows: Spark 32, Snowflake 32
- rows matched: 32 of 32 → **MATCH**

### gold_flashboot_hit_rate

- rows: Spark 15, Snowflake 15
- rows matched: 15 of 15 → **MATCH**

### gold_engine_comparison

- rows: Spark 12, Snowflake 12
- rows matched: 12 of 12 → **MATCH**

### gold_worker_boot_phases

- rows: Spark 18, Snowflake 18
- rows matched: 18 of 18 → **MATCH**

### gold_cost_per_job

- rows: Spark 16, Snowflake 16
- rows matched: 16 of 16 → **MATCH**

### gold_scoring_cost_per_batch

- rows: Spark 14, Snowflake 14
- rows matched: 14 of 14 → **MATCH**

### gold_sweep_latency

- rows: Spark 38, Snowflake 38
- rows matched: 38 of 38 → **MATCH**

### gold_coldstart_events

- rows: Spark 47, Snowflake 47
- rows matched: 47 of 47 → **MATCH**

