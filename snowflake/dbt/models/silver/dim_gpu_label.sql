-- seed: one Pulse/emberserve GPU label → tier, GPU model (evidence-graded), $/hr (seeds/gpu_labels.csv)
select * from {{ ref('gpu_labels') }}
