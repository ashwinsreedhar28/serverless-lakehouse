-- n_hits ≤ n_cold, rate in [0, 1], and the rate is exactly n_hits / n_cold rounded to 3 places.
select *
from {{ ref('gold_flashboot_hit_rate') }}
where n_hits > n_cold
   or hit_rate < 0 or hit_rate > 1
   or (n_cold > 0 and abs(hit_rate - round(n_hits::double / n_cold, 3)) > 1e-9)
   or (n_cold = 0 and hit_rate is not null)
