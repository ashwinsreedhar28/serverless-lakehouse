-- Silver decision: is_flashboot_hit is defined only for cold requests, true only when ok and delay_ms < the threshold.
select *
from {{ ref('silver_coldstart_requests') }}
where (kind != 'cold' and is_flashboot_hit is not null)
   or (is_flashboot_hit and (not ok or delay_ms >= {{ var('flashboot_hit_ms') }}))
