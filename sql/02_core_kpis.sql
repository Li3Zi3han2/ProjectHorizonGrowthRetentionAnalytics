-- Calendar-day rolling unique users; returned means a preceding gap >=7 days.
WITH activity AS (SELECT DISTINCT user_id,session_date FROM horizon.sessions),
ordered AS (SELECT a.*,u.register_date,lag(session_date) OVER(PARTITION BY user_id ORDER BY session_date) prev FROM activity a JOIN horizon.users u USING(user_id)),
calendar AS (SELECT generate_series(DATE '2026-01-01',DATE '2026-06-29','1 day')::date AS day)
SELECT to_char(c.day,'YYYY-MM-DD') AS day,
 (SELECT count(*) FROM horizon.users WHERE register_date=c.day) new_users,
 count(o.user_id) dau,
 count(o.user_id) FILTER(WHERE o.session_date=o.register_date) new_active,
 count(o.user_id) FILTER(WHERE o.session_date<>o.register_date AND o.session_date-o.prev<7) retained,
 count(o.user_id) FILTER(WHERE o.session_date<>o.register_date AND o.session_date-o.prev>=7) returned,
 (SELECT count(DISTINCT user_id) FROM activity WHERE session_date BETWEEN c.day-6 AND c.day) wau,
 (SELECT count(DISTINCT user_id) FROM activity WHERE session_date BETWEEN c.day-29 AND c.day) mau
FROM calendar c LEFT JOIN ordered o ON o.session_date=c.day GROUP BY c.day ORDER BY c.day;
