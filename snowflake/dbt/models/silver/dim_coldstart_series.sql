-- seed: one cold-start series → engine, model, GPU, FlashBoot setting, weights mode (seeds/coldstart_series.csv)
select * from {{ ref('coldstart_series') }}
