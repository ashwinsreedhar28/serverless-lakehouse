-- Spark: audit round 4 — the cohort rows reproduce the pooled row (a cohort with warm requests but no full boot keeps its
-- row with n_full_boots = 0 so the sums hold).
with pooled as (
    select engine, weights_mode, n_full_boots, n_warm, n_undated from {{ ref('gold_engine_comparison') }} where scope = 'pooled'
),
cohorts as (
    select engine, weights_mode, sum(n_full_boots) as n_full_boots, sum(n_warm) as n_warm, sum(n_undated) as n_undated
    from {{ ref('gold_engine_comparison') }} where scope = 'cohort' group by 1, 2
)
select p.engine, p.weights_mode, p.n_full_boots, c.n_full_boots as cohort_full_boots, p.n_warm, c.n_warm as cohort_warm
from pooled p
full outer join cohorts c on c.engine = p.engine and c.weights_mode = p.weights_mode
where p.n_full_boots is distinct from c.n_full_boots
   or p.n_warm is distinct from c.n_warm
   or p.n_undated is distinct from c.n_undated
