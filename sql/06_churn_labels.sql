-- Mature D30 cohort; zero active days in D22-D30 is churn, not exact-day D30 loss.
SELECT u.user_id,CASE WHEN count(s.user_id)=0 THEN 1 ELSE 0 END churn_30
FROM horizon.users u LEFT JOIN horizon.sessions s ON s.user_id=u.user_id AND s.session_date BETWEEN u.register_date+22 AND u.register_date+30
WHERE u.register_date+30<=DATE '2026-06-29' GROUP BY u.user_id ORDER BY u.user_id;
