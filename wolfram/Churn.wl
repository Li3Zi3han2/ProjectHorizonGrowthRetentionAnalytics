HChurn::usage="HChurn[] fits D0-D7 logistic and gradient-boosted models with temporal cohorts.";
$HNumeric={"sessions_d0_7","active_days_d0_7","total_minutes_d0_7","avg_session_minutes","tutorial_completed","core_loop_unlocked","chapter_reached_d7","boss_attempts_d0_7","boss_failure_rate_d0_7","social_interactions_d0_7","activity_participation_d0_7","crash_rate_d0_7","fps_quality","first_purchase_flag_d0_7","spend_d0_7","registration_week"};
$HCategories=<|"market"->{"CN","DE","JP","KR","US"},"channel"->{"creator","cross_promo","organic","referral","store_feature","video_ads"},"device"->{"Android","PC","iOS"}|>;
HX[r_]:=N[Join[Lookup[r,$HNumeric],Flatten[KeyValueMap[Function[{k,v},Boole[r[k]==#]&/@Rest[v]],$HCategories]]]];
HSig[z_]:=1./(1.+Exp[-Clip[z,{-35.,35.}]]);
HLogit[x_,y_]:=Module[{b=ConstantArray[0.,Length[First[x]]],p,w,h,g,delta},Do[p=HSig/@(x.b);w=p(1-p);g=Transpose[x].(p-y)+.0001 b;h=Transpose[x].(x*w)+.0001 IdentityMatrix[Length[b]];delta=LinearSolve[h,g];b-=delta;If[Max[Abs[delta]]<1.*^-8,Break[]],{40}];b];
HEvaluate[y_,p_]:=Module[{yi=Round[y],ord,t,k,n=Length[y],pos=Total[y],tp,fp,auc,ap,top,cm,pred,precision,recall},ord=Reverse[Ordering[p]];t=yi[[ord]];tp=Accumulate[t];fp=Accumulate[1-t];
 (* Group tied probabilities for exact trapezoid AUC and average precision. *)
 k=Join[Flatten[Position[Differences[p[[ord]]],v_/;v!=0]],{n}];
 auc=Total[Differences[Prepend[fp[[k]],0]] (Most[Prepend[tp[[k]],0]]+tp[[k]])/2]/(pos (n-pos));
 ap=Total[Differences[Prepend[tp[[k]],0]] (tp[[k]]/k)]/pos;
 top=Take[ord,Ceiling[n/10]];pred=Boole[#>=.5]&/@p;cm=Table[Count[Transpose[{yi,pred}],{a,b}],{a,0,1},{b,0,1}];HAssert[Total[Flatten[cm]]==n,"confusion matrix population"];precision=N[cm[[2,2]]/Max[1,Total[cm[[All,2]]]]];recall=N[cm[[2,2]]/Max[1,pos]];
 <|"roc_auc"->N[auc],"pr_auc"->N[ap],"brier"->Mean[(p-y)^2],"precision"->precision,"recall"->recall,"f1"->2 precision recall/Max[1.*^-12,precision+recall],"confusion_matrix"->cm,"threshold"->.5,"lift_at_10pct"->N[Mean[y[[top]]]/Mean[y]],"capture_at_10pct"->N[Total[y[[top]]]/pos]|>];
HChurn[]:=Module[{f,x,y,train,val,test,mu,sd,z,b,p,booster,bp,fitrows,names,coefs,eval,subset,cal},
 f=HSQLFile["05_user_features.sql"];HCSV[HPath["outputs","tables","wolfram_features.csv"],f];HAssert[Max[Lookup[f,"max_feature_day"]]<=7,"leakage"];
 x=HX/@f;y=N[Lookup[f,"churn_30"]];train=Flatten[Position[Lookup[f,"registration_day"],d_/;d<=89]];val=Flatten[Position[Lookup[f,"registration_day"],d_/;89<d<=119]];test=Flatten[Position[Lookup[f,"registration_day"],d_/;d>119]];
 HAssert[Min[Length/@{train,val,test}]>20,"temporal cohorts"];mu=Mean[x[[train]]];sd=StandardDeviation[x[[train]]]/. {0.->1.,0->1.};z=Prepend[(#-mu)/sd,1.]&/@x;
 b=HLogit[z[[train]],y[[train]]];p=HSig/@(z.b);eval=HEvaluate[y[[test]],p[[test]]];
 names=Join[$HNumeric,Flatten[KeyValueMap[Function[{k,v},(k<>"="<>#)&/@Rest[v]],$HCategories]]];coefs=MapThread[<|"feature"->#1,"coefficient"->#2,"odds_ratio_per_sd"->Exp[#2]|>&,{names,Rest[b]}];HCSV[HPath["outputs","tables","logistic_coefficients.csv"],coefs];
 subset=Take[train,UpTo[$HC["NonlinearCap"]]];SeedRandom[$HC["Seed"]];HLog["Training Wolfram gradient boosted trees"];
 booster=Classify[x[[subset]]->Round[y[[subset]]],Method->{"GradientBoostedTrees",MaxTrainingRounds->80,"MaxDepth"->4,"LeafSize"->30},ValidationSet->(x[[val]]->Round[y[[val]]]),RecalibrationFunction->None,PerformanceGoal->"Quality"];
 HAssert[Head[booster]===ClassifierFunction,"nonlinear Wolfram model"];bp=booster[x[[test]],"Probability"->1];
 HCSV[HPath["outputs","models","wolfram_predictions.csv"],MapThread[<|"user_id"->#1,"churn_30"->#2,"logistic"->#3,"nonlinear"->#4|>&,{Lookup[f[[test]],"user_id"],y[[test]],p[[test]],bp}]];
 HJSON[HPath["outputs","models","wolfram_evaluation.json"],<|"logistic"->eval,"nonlinear"->HEvaluate[y[[test]],bp],"train_n"->Length[train],"validation_n"->Length[val],"test_n"->Length[test],"nonlinear_train_n"->Length[subset],"feature_names"->names|>];
 Export[HPath["outputs","models","wolfram_booster.wxf"],booster,"WXF"];Export[HPath["outputs","models","wolfram_logistic.wxf"],<|"coefficients"->b,"mean"->mu,"sd"->sd,"features"->names|>,"WXF"];
 $HM["churn/sample"]=Length[f];$HM["churn/positive"]=Total[y];$HM["churn/train"]=Length[train];$HM["churn/validation"]=Length[val];$HM["churn/test"]=Length[test];eval];
