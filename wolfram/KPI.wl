HKPI::usage="HKPI[] calculates calendar KPI and revenue from raw facts.";
HKPI[]:=Module[{daily,pay},daily=HSQLFile["02_core_kpis.sql"];HCSV[HPath["outputs","tables","daily_kpis.csv"],daily];
 pay=First[HQuery["SELECT count(DISTINCT user_id) payers,coalesce(sum(amount_usd),0)::float8 revenue FROM horizon.monetization"]];
 $HM["users"]=$HC["Users"];$HM["payers"]=pay["payers"];$HM["revenue"]=pay["revenue"];
 $HM["payer_conversion"]=N[pay["payers"]/$HC["Users"]];$HM["arpu"]=pay["revenue"]/$HC["Users"];$HM["arppu"]=pay["revenue"]/Max[1,pay["payers"]];
 Do[Do[$HM["daily/"<>r["day"]<>"/"<>k]=r[k],{k,{"new_users","dau","new_active","retained","returned","wau","mau"}}],{r,daily}];
 $HM["activation_rate"]=N[First[HQuery["SELECT count(DISTINCT e.user_id)::float8 n FROM horizon.gameplay_events e JOIN horizon.users u USING(user_id) WHERE event_type='core_loop_unlock' AND event_time::date<=u.register_date+7 AND u.register_date+7<=DATE '2026-06-29'"]]["n"]/First[HQuery["SELECT count(*) n FROM horizon.users WHERE register_date+7<=DATE '2026-06-29'"]]["n"]];daily];
