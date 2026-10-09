-- No events later than D7 enter features. Labels live in a separate CTE.
WITH s AS (SELECT u.user_id,count(*) sessions_d0_7,count(DISTINCT session_date) active_days_d0_7,
 sum(session_minutes)::float8 total_minutes_d0_7,avg(session_minutes)::float8 avg_session_minutes,
 avg(crash_flag)::float8 crash_rate_d0_7,avg(fps_quality_bucket)::float8 fps_quality,
 max(session_date-u.register_date) max_feature_day
 FROM horizon.users u JOIN horizon.sessions s ON s.user_id=u.user_id AND s.session_date BETWEEN u.register_date AND u.register_date+7 GROUP BY u.user_id),
p AS (SELECT u.user_id,max(chapter) chapter_reached_d7,max(tutorial_completed) tutorial_completed,max(core_loop_unlocked) core_loop_unlocked,sum(boss_attempts) boss_attempts_d0_7,
 sum(boss_failures)::float8/NULLIF(sum(boss_attempts),0) boss_failure_rate_d0_7 FROM horizon.users u JOIN horizon.progression p ON p.user_id=u.user_id AND p.event_date BETWEEN u.register_date AND u.register_date+7 GROUP BY u.user_id),
e AS (SELECT u.user_id,count(*) FILTER(WHERE event_type='social_interaction') social_interactions_d0_7,count(*) FILTER(WHERE event_type='activity_enter') activity_participation_d0_7 FROM horizon.users u JOIN horizon.gameplay_events e ON e.user_id=u.user_id AND e.event_time::date BETWEEN u.register_date AND u.register_date+7 GROUP BY u.user_id),
m AS (SELECT u.user_id,count(*) first_purchase_flag_d0_7,sum(amount_usd)::float8 spend_d0_7 FROM horizon.users u JOIN horizon.monetization m ON m.user_id=u.user_id AND m.transaction_date BETWEEN u.register_date AND u.register_date+7 GROUP BY u.user_id),
labels AS (SELECT u.user_id,CASE WHEN count(s.user_id)=0 THEN 1 ELSE 0 END churn_30 FROM horizon.users u LEFT JOIN horizon.sessions s ON s.user_id=u.user_id AND s.session_date BETWEEN u.register_date+22 AND u.register_date+30 GROUP BY u.user_id)
SELECT u.user_id,to_char(u.register_date,'YYYY-MM-DD') register_date,u.register_date-DATE '2026-01-01' registration_day,
 s.sessions_d0_7,s.active_days_d0_7,s.total_minutes_d0_7,s.avg_session_minutes,p.tutorial_completed,p.core_loop_unlocked,p.chapter_reached_d7,p.boss_attempts_d0_7,coalesce(p.boss_failure_rate_d0_7,0) boss_failure_rate_d0_7,
 coalesce(e.social_interactions_d0_7,0) social_interactions_d0_7,coalesce(e.activity_participation_d0_7,0) activity_participation_d0_7,s.crash_rate_d0_7,s.fps_quality,
 CASE WHEN coalesce(m.first_purchase_flag_d0_7,0)>0 THEN 1 ELSE 0 END first_purchase_flag_d0_7,coalesce(m.spend_d0_7,0) spend_d0_7,u.market,u.acquisition_channel channel,u.device,floor((u.register_date-DATE '2026-01-01')/7.0)::int registration_week,s.max_feature_day,l.churn_30
FROM horizon.users u JOIN s USING(user_id) JOIN p USING(user_id) LEFT JOIN e USING(user_id) LEFT JOIN m USING(user_id) JOIN labels l USING(user_id)
WHERE u.register_date+30<=DATE '2026-06-29' ORDER BY u.user_id;
