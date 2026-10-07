-- seed: per-request GPU label corrections where the recorded label was not the placement (seeds/coldstart_request_overrides.csv)
select * from {{ ref('coldstart_request_overrides') }}
