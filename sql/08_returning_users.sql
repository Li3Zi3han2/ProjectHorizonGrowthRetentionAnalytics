-- Patch2 eligible: registered before Day106 and no activity during Day106-Day119.
WITH eligible AS (SELECT u.user_id FROM horizon.users u WHERE u.register_date<DATE '2026-04-17' AND NOT EXISTS(SELECT 1 FROM horizon.sessions s WHERE s.user_id=u.user_id AND s.session_date BETWEEN DATE '2026-04-17' AND DATE '2026-04-30')),
returns AS (SELECT e.user_id,min(s.session_date) return_date FROM eligible e JOIN horizon.sessions s USING(user_id) WHERE s.session_date BETWEEN DATE '2026-05-01' AND DATE '2026-05-07' GROUP BY e.user_id),
post AS (SELECT r.user_id,count(DISTINCT s.session_date) days7 FROM returns r JOIN horizon.sessions s ON s.user_id=r.user_id AND s.session_date BETWEEN r.return_date AND r.return_date+6 GROUP BY r.user_id)
SELECT (SELECT count(*) FROM eligible) eligible,(SELECT count(*) FROM returns) returned,coalesce((SELECT avg(days7)::float8 FROM post),0) post_return_days7;
