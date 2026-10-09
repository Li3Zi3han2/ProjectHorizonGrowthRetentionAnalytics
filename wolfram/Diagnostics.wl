(* Native diagnostics previously supplied only by the Python report adapter. *)
HDiagnostics[]:=Module[{f=HReadTable["wolfram_features.csv"],cols,values,matrix,correlation,multi,q,pred,ord,y,bins,lift},
 cols={"sessions_d0_7","active_days_d0_7","total_minutes_d0_7","avg_session_minutes"};
 values=Table[N[Lookup[f,c]],{c,cols}];matrix=Table[Correlation[values[[i]],values[[j]]],{i,4},{j,4}];
 Export[HPath["outputs","tables","feature_correlations.csv"],Prepend[MapThread[Prepend,{matrix,cols}],Prepend[cols,"feature"]],"CSV"];
 correlation=Correlation[values[[1]],values[[2]]];multi=N[Count[MapThread[Greater,{values[[1]],values[[2]]}],True]/Length[f]];
 HJSON[HPath["outputs","validation","feature_diagnostics.json"],<|"session_active_day_correlation"->correlation,"fraction_users_multiple_sessions"->multi,"note"->"Correlated predictors are one behavior family, not independent causal effects."|>];
 q="WITH daily AS(SELECT user_id,session_date,max(crash_flag) crash,avg(fps_quality_bucket)::float8 fps FROM horizon.sessions GROUP BY 1,2) SELECT device,CASE WHEN session_date<DATE '2026-03-02' THEN 'pre_patch1' ELSE 'post_patch1' END period,count(*) active_user_days,avg(crash)::float8 crash_rate,avg(fps)::float8 mean_fps FROM daily JOIN horizon.users u USING(user_id) WHERE session_date-register_date BETWEEN 0 AND 7 GROUP BY 1,2 ORDER BY 1,2";
 HCSV[HPath["outputs","tables","device_performance.csv"],HQuery[q]];
 q="WITH eligible AS(SELECT * FROM horizon.users u WHERE register_date<DATE '2026-04-17' AND NOT EXISTS(SELECT 1 FROM horizon.sessions s WHERE s.user_id=u.user_id AND session_date BETWEEN DATE '2026-04-17' AND DATE '2026-04-30')) SELECT device,count(*) count,avg((EXISTS(SELECT 1 FROM horizon.sessions s WHERE s.user_id=e.user_id AND session_date BETWEEN DATE '2026-05-01' AND DATE '2026-05-07'))::int)::float8 mean FROM eligible e GROUP BY device ORDER BY device";
 HCSV[HPath["outputs","tables","reactivation_device.csv"],HQuery[q]];
 pred=Rest[Import[HPath["outputs","models","wolfram_predictions.csv"],"CSV"]];ord=Reverse[Ordering[pred[[All,3]]]];y=N[pred[[ord,2]]];
 bins=Floor[Range[0,Length[y]-1]*10/Length[y]]+1;
 lift=Table[<|"decile"->d,"churn_30"->Mean[Pick[y,bins,d]]/Mean[y]|>,{d,1,10}];HCSV[HPath["outputs","tables","risk_decile_lift.csv"],lift];
];
