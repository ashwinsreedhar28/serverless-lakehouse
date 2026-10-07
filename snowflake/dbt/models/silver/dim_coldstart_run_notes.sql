-- seed: per-run facts (host state) that neither the files nor the series carry (seeds/coldstart_run_notes.csv)
select * from {{ ref('coldstart_run_notes') }}
