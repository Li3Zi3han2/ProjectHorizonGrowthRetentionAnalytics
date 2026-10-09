-- Chronology, monotone progression and usable windows. Foreign keys enforce identity.
WITH regressions AS (
 SELECT chapter < lag(chapter) OVER(PARTITION BY user_id ORDER BY event_date) AS bad FROM horizon.progression
)
SELECT 'event_before_registration' AS check_name,count(*) AS failures
FROM horizon.gameplay_events e JOIN horizon.users u USING(user_id) WHERE e.event_time::date < u.register_date
UNION ALL SELECT 'session_before_registration',count(*) FROM horizon.sessions s JOIN horizon.users u USING(user_id) WHERE s.session_date<u.register_date
UNION ALL SELECT 'future_session',count(*) FROM horizon.sessions WHERE session_date>DATE '2026-06-29'
UNION ALL SELECT 'future_event',count(*) FROM horizon.gameplay_events WHERE event_time::date>DATE '2026-06-29'
UNION ALL SELECT 'progression_regression',count(*) FROM regressions WHERE bad
UNION ALL SELECT 'invalid_minutes',count(*) FROM horizon.sessions WHERE session_minutes<=0
UNION ALL SELECT 'negative_payment',count(*) FROM horizon.monetization WHERE amount_usd<0
UNION ALL SELECT 'invalid_registration',count(*) FROM horizon.users WHERE register_date NOT BETWEEN DATE '2026-01-01' AND DATE '2026-06-29';
