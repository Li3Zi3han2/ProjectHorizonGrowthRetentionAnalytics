-- Exact-day retention with separate mature denominators for each horizon.
WITH horizons AS (SELECT generate_series(0,30) d), active AS (SELECT DISTINCT user_id,session_date FROM horizon.sessions)
SELECT h.d,count(u.user_id) eligible,count(a.user_id) retained,
 count(a.user_id)::double precision/NULLIF(count(u.user_id),0) rate
FROM horizons h JOIN horizon.users u ON u.register_date+h.d<=DATE '2026-06-29'
LEFT JOIN active a ON a.user_id=u.user_id AND a.session_date=u.register_date+h.d
GROUP BY h.d ORDER BY h.d;
