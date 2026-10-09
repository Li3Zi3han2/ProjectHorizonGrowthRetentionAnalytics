-- Gate experiment A: first Level 12 attempt; exposure day 0 through day 3 inclusive.
-- Exclude exposures without complete followup, never condition eligibility on clearing.
WITH first_gate AS (
 SELECT user_id,min(event_date) first_gate_date FROM horizon.progression
 WHERE level=12 AND boss_attempts>0 GROUP BY user_id
)
SELECT g.user_id,to_char(g.first_gate_date,'YYYY-MM-DD') first_gate_date,
 coalesce(bool_or(p.chapter>=3),false)::int completed_within3
FROM first_gate g LEFT JOIN horizon.progression p ON p.user_id=g.user_id
 AND p.event_date BETWEEN g.first_gate_date AND g.first_gate_date+3
WHERE g.first_gate_date+3<=DATE '2026-06-29'
GROUP BY g.user_id,g.first_gate_date ORDER BY g.user_id;
