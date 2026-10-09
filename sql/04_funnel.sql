-- Six core stages; optional adoption independently uses Chapter 3 completers.
WITH steps AS (SELECT * FROM (VALUES (1,'Register'),(2,'tutorial_start'),(3,'tutorial_complete'),(4,'core_loop_unlock'),(5,'chapter_2'),(6,'chapter_3'),(7,'activity_enter'),(8,'social_interaction')) t(step,name)),
flags AS (SELECT u.user_id,u.device,u.market,u.acquisition_channel,
 bool_or(e.event_type='tutorial_start') s2,bool_or(e.event_type='tutorial_complete') s3,
 bool_or(e.event_type='core_loop_unlock') s4,bool_or(e.event_type='chapter_complete' AND e.event_value>=2) s5,
 bool_or(e.event_type='chapter_complete' AND e.event_value>=3) s6,
 bool_or(e.event_type='activity_enter') s7,bool_or(e.event_type='social_interaction') s8
 FROM horizon.users u LEFT JOIN horizon.gameplay_events e ON e.user_id=u.user_id AND e.event_time::date BETWEEN u.register_date AND u.register_date+7
 WHERE u.register_date+7<=DATE '2026-06-29' GROUP BY u.user_id),
expanded AS (SELECT f.*,s.*,CASE WHEN s.step<=6 THEN 'core' ELSE 'optional' END stage_type,CASE s.step WHEN 1 THEN true WHEN 2 THEN s2 WHEN 3 THEN s2 AND s3 WHEN 4 THEN s2 AND s3 AND s4 WHEN 5 THEN s2 AND s3 AND s4 AND s5 WHEN 6 THEN s2 AND s3 AND s4 AND s5 AND s6 WHEN 7 THEN s2 AND s3 AND s4 AND s5 AND s6 AND s7 WHEN 8 THEN s2 AND s3 AND s4 AND s5 AND s6 AND s8 END passed FROM flags f CROSS JOIN steps s)
SELECT 'overall' dimension,'all' category,step,name,stage_type,count(*) FILTER(WHERE passed) n FROM expanded GROUP BY step,name,stage_type
UNION ALL SELECT 'device',device,step,name,stage_type,count(*) FILTER(WHERE passed) FROM expanded GROUP BY device,step,name,stage_type
UNION ALL SELECT 'market',market,step,name,stage_type,count(*) FILTER(WHERE passed) FROM expanded GROUP BY market,step,name,stage_type
UNION ALL SELECT 'channel',acquisition_channel,step,name,stage_type,count(*) FILTER(WHERE passed) FROM expanded GROUP BY acquisition_channel,step,name,stage_type
ORDER BY dimension,category,step;
