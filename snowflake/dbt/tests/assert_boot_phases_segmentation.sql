-- Spark: tests/test_gold_boot_phases.py. (1) boot 0 (lines before any opener) is a row only when it carries a phase;
-- (2) a boot opened by a wrapper line has t_start_vllm, one opened by an orphan init does not; (3) graph_capture_s is the
-- sum over the passes counted in n_graph_passes, so a boot with passes has a value and one without has none.
select source_file, boot_index, segmented_by, 'boot 0 without a phase' as problem
from {{ ref('gold_worker_boot_phases') }}
where boot_index = 0 and weights_load_s is null and start_to_api_ready_s is null and init_engine_s is null and graph_capture_s is null
union all
select source_file, boot_index, segmented_by, 'wrapper-anchored boot without t_start_vllm'
from {{ ref('gold_worker_boot_phases') }}
where segmented_by like 'Starting vLLM%' and t_start_vllm is null
union all
select source_file, boot_index, segmented_by, 'init-anchored boot with a t_start_vllm'
from {{ ref('gold_worker_boot_phases') }}
where segmented_by like 'Initializing%' and t_start_vllm is not null
union all
select source_file, boot_index, segmented_by, 'graph passes and graph_capture_s disagree'
from {{ ref('gold_worker_boot_phases') }}
where (n_graph_passes > 0) != (graph_capture_s is not null)
