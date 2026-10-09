-- Snapshot at end of simulation, exclusive priority rules; D7 risk proxies are observable.
WITH s AS (SELECT user_id,max(session_date) last_date,count(DISTINCT session_date) FILTER(WHERE session_date>=DATE '2026-06-02') active28,sum(session_minutes) FILTER(WHERE session_date>=DATE '2026-06-02') minutes28 FROM horizon.sessions GROUP BY user_id),
m AS (SELECT user_id,sum(amount_usd)::float8 spend FROM horizon.monetization GROUP BY user_id),
p AS (SELECT user_id,max(chapter) chapter FROM horizon.progression GROUP BY user_id),
gaps AS (SELECT user_id,session_date,session_date-lag(session_date) OVER(PARTITION BY user_id ORDER BY session_date) gap FROM (SELECT DISTINCT user_id,session_date FROM horizon.sessions) activity),
r AS (SELECT DISTINCT user_id FROM gaps WHERE gap>=7 AND session_date>=DATE '2026-06-23'),
base AS (SELECT u.user_id,coalesce(s.active28,0) active28,coalesce(s.minutes28,0)::float8 minutes28,p.chapter,coalesce(m.spend,0) spend,
 CASE WHEN u.register_date>=DATE '2026-06-23' AND p.chapter<1 THEN 'New & Unactivated'
 WHEN r.user_id IS NOT NULL THEN 'Returning Users' WHEN coalesce(m.spend,0)>=50 THEN 'High-Value Users'
 WHEN u.register_date>=DATE '2026-06-23' THEN 'Healthy New Users' WHEN s.last_date<DATE '2026-06-23' THEN 'At-Risk Users'
 WHEN coalesce(s.active28,0)>=10 AND coalesce(m.spend,0)=0 THEN 'Highly Engaged Non-Payers' ELSE 'Core Engaged Users' END segment
 FROM horizon.users u JOIN s USING(user_id) JOIN p USING(user_id) LEFT JOIN m USING(user_id) LEFT JOIN r USING(user_id))
SELECT segment,count(*) n,avg(active28)::float8 active_days28,avg(minutes28)::float8 minutes28,avg(chapter)::float8 chapter,avg((spend>0)::int)::float8 payer_rate FROM base GROUP BY segment ORDER BY segment;
