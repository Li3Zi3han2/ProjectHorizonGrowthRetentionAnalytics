HGenerate::usage="HGenerate[c] simulates players in Wolfram, bulk loads seven facts via a transport-only COPY adapter.";
(* Compiled state transition; latent engagement, skill, social and spending never enter models. *)
$HSim=Compile[{{reg,_Integer},{eng,_Real},{skill,_Real},{soc,_Real},{fit,_Real},{spend,_Real},{mobile,_Integer},{android,_Integer},{quality,_Real},{rr,_Real,2}},
 Module[{out=Table[0.,{180},{12}],alive=1,streak=0,n=0,ch=0,tut=0,core=0,active=0,att=0,fail=0,fps=3,crash=0,wall=0.,p=0.,social=0,activity=0,socialn=0,paid=0,money=0.,minutes=0.,d=0,k=0},
 For[d=reg,d<180,d++,k=d-reg+1;
  (* Tenure decay affects visits, while state attrition creates longer silence spells. *)
  p=If[alive==1,Max[.03,.16+.22 eng+.08 fit+.16 Exp[-(k-1)/3.]-.025 mobile-.045 android-.035 wall],.0015+.002 eng];
  If[d>=120&&d<=124&&streak>=14,p=Max[p,.008+.015 eng+.010 Min[1.,n/15.]+.006 Min[1.,ch/3.]+.009 Min[1.,socialn/5.]+.008 paid+.008 quality]];
  active=If[k==1||rr[[k,1]]<p,1,0];
  If[active==1,
   If[alive==0,alive=1];streak=0;n++;att=0;fail=0;social=0;activity=0;money=0.;
   fps=If[android==1&&rr[[k,2]]<If[d<60,.48,.20],1,If[rr[[k,2]]<.72,2,3]];
   crash=If[rr[[k,3]]<If[fps==1,.13,.017],1,0];
   If[tut==0&&rr[[k,4]]<.76+.13 eng,tut=1];
   If[tut==1&&core==0&&rr[[k,5]]<.73+.13 fit,core=1;ch=1];
   If[core==1&&ch==1&&n>=2&&rr[[k,6]]<.75,ch=2];
   If[ch==2&&n>=2,att=1+If[rr[[k,7]]<.5,1,0];
    If[rr[[k,8]]<1.-(1.-(.22+.45 skill+.10 fit-.065 mobile))^att,ch=3;fail=att-1;wall=0.,fail=att;wall=1.]];
   If[ch>=3&&n>=12&&Mod[n,8]==0,ch=Min[6,ch+1]];
   If[ch>=3&&rr[[k,9]]<.46+.28 fit+If[d>=120,.08,0.],activity=1];
   If[ch>=3&&activity==1&&rr[[k,10]]<.10+.40 soc+.15 eng,social=1];
   If[rr[[k,11]]<If[paid==0,.001+.003 spend+.001 eng+.0005 fit+.0005 Min[1.,ch/3.],.02+.03 spend],money=If[rr[[k,12]]<.7,4.99,19.99]];
   socialn+=social;If[money>0,paid=1];
   minutes=Max[2.,(18.+36. eng+12. fit+12. rr[[k,12]]) (1.-.45 crash)];
   out[[k]]={1. d,1. ch,1. tut,1. core,1. att,1. fail,minutes,1. fps,1. crash,1. social,1. activity,money};
   If[rr[[k,13]]<.04+.06(1.-eng)+.14 Exp[-(k-1)/6.]+.04 wall+.05 crash,alive=0],streak++];
 ];out],CompilationTarget->"WVM",RuntimeOptions->"Speed"];
HDate[d_]:=$HDates[[d+1]];
HGenerate[c_]:=Module[{tables={"users","sessions","progression","gameplay_events","monetization","acquisition","content_exposure"},batch,rows,result,u,reg,market,channel,campaign,device,arch,quality,eng,skill,soc,fit,spend,rr,sim,day,ch,tut,core,att,fail,sn,dayn,ns,weights,oldch,oldtut,oldcore,eid=0,sid=0,tid=0,events,kind,value,date,headers},
 headers=<|"users"->{"user_id","register_date","market","acquisition_channel","campaign","device","platform","age_bucket","latent_player_archetype","acquisition_quality"},"sessions"->{"session_id","user_id","session_date","session_number","session_minutes","device","fps_quality_bucket","crash_flag"},"progression"->{"user_id","event_date","chapter","level","tutorial_completed","core_loop_unlocked","boss_attempts","boss_failures"},"gameplay_events"->{"event_id","user_id","event_time","event_type","event_value"},"monetization"->{"transaction_id","user_id","transaction_date","product_type","amount_usd"},"acquisition"->{"user_id","market","channel","campaign","creative","acquisition_date"},"content_exposure"->{"user_id","date","content_type","content_id","exposed","clicked"}|>;
 $HDates=Table[DateString[DatePlus[DateObject[c["Start"]],day],{"Year","-","Month","-","Day"}],{day,0,179}];
 If[!DirectoryQ[HPath["outputs","staging"]],CreateDirectory[HPath["outputs","staging"],CreateIntermediateDirectories->True]];HBridge[{"reset"}];
 Do[
 rows=AssociationThread[tables,Table[{},Length[tables]]];
 result=Reap[Do[
  SeedRandom[c["Seed"]+u,Method->"MersenneTwister"];
  reg=RandomChoice[Table[1.+.004 j+.6 Boole[120<=j<=127],{j,0,179}]->Range[0,179]];
  market=RandomChoice[{.25,.18,.12,.3,.15}->{"CN","JP","KR","US","DE"}];
  channel=RandomChoice[{.20,.10,.17,.32,.09,.12}->{"organic","store_feature","creator","video_ads","referral","cross_promo"}];
  device=RandomChoice[{.25,.3,.45}->{"PC","iOS","Android"}];arch=RandomChoice[{"story","combat","collector","social","casual"}];
  quality=Clip[.48+Lookup[<|"organic"->.10,"creator"->If[MemberQ[{"JP","KR"},market],.12,.04],"video_ads"->-.06,"referral"->.12,"cross_promo"->.02|>,channel,0]+RandomVariate[NormalDistribution[0,.15]],{.05,.95}];
  campaign=channel<>"_"<>ToString[RandomInteger[{1,3}]];If[campaign=="video_ads_3",quality=Max[.05,quality-.09]];
  eng=Clip[.35+.4 quality+RandomVariate[NormalDistribution[0,.19]],{.03,.98}];skill=Clip[RandomReal[]+.20 Boole[arch=="combat"]-.20 Boole[arch=="casual"],{.05,.95}];
  soc=Clip[RandomReal[]+.25 Boole[channel=="referral"]+.2 Boole[arch=="social"],{0.,1.}];fit=RandomReal[{.25,.95}];spend=RandomReal[];
  Sow[{u,HDate[reg],market,channel,campaign,device,If[device=="PC","desktop","mobile"],RandomChoice[{"18-24","25-34","35+"}],arch,quality},"users"];
  Sow[{u,market,channel,campaign,"creative_"<>ToString[Mod[u,4]+1],HDate[reg]},"acquisition"];
  rr=RandomReal[1.,{180,13}];sim=$HSim[reg,eng,skill,soc,fit,spend,Boole[device!="PC"],Boole[device=="Android"],quality,rr];
  sim=Select[Take[sim,180-reg],#[[7]]>0&];sn=0;dayn=0;oldch=0;oldtut=0;oldcore=0;
  Do[day=Round[r[[1]]];date=HDate[day];ch=Round[r[[2]]];tut=Round[r[[3]]];core=Round[r[[4]]];att=Round[r[[5]]];fail=Round[r[[6]]];dayn++;
   (* Split observed daily minutes; daily state and events execute once. *)
   ns=1+Boole[RandomReal[]<.15+.25 eng]+Boole[RandomReal[]<.025+.035 eng];weights=RandomReal[{.7,1.3},ns];weights=weights/Total[weights];
   Do[sn++;sid++;Sow[{sid,u,date,sn,r[[7]] weights[[j]],device,Round[r[[8]]],If[j==1,Round[r[[9]]],0]},"sessions"],{j,ns}];
   Sow[{u,date,ch,If[ch==2,12,Max[1,ch*4]],tut,core,att,fail},"progression"];
   events={};If[dayn==1,AppendTo[events,{"tutorial_start",1}]];
   If[tut>oldtut,AppendTo[events,{"tutorial_complete",1}]];If[core>oldcore,AppendTo[events,{"core_loop_unlock",1}]];
   If[ch>oldch,Do[AppendTo[events,{"chapter_complete",cc}],{cc,oldch+1,ch}]];
   If[att>0,AppendTo[events,{"boss_attempt",att}];If[fail<att,AppendTo[events,{"boss_clear",1}]]];
   If[r[[11]]>0,events=Join[events,{{"activity_enter",1},{"activity_complete",1}}]];
   If[ch>=3&&oldch<3,AppendTo[events,{"social_unlock",1}]];
   If[r[[10]]>0,AppendTo[events,{"social_interaction",1}]];
   Do[eid++;Sow[{eid,u,date<>" 12:"<>IntegerString[ei,10,2]<>":00",events[[ei,1]],events[[ei,2]]},"gameplay_events"],{ei,Length[events]}];
   If[r[[12]]>0,tid++;Sow[{tid,u,date,"starter_or_cosmetic",r[[12]]},"monetization"]];
   If[Mod[day,7]==0,Sow[{u,date,If[day>=120,"patch2_event","weekly_content"],"content_"<>ToString[Quotient[day,7]],1,Boole[r[[11]]>0]},"content_exposure"]];
   oldch=ch;oldtut=tut;oldcore=core,
  {r,sim}],{u,batch,Min[c["Users"],batch+c["BatchSize"]-1]}],_,Rule];
 rows=Join[rows,Association[result[[2]]]];
 Do[Export[HPath["outputs","staging",t<>".csv"],Prepend[rows[t],headers[t]],"CSV"],{t,tables}];HBridge[{"load"}];
 If[Mod[batch-1,10000]==0,HLog["Generated / loaded users "<>ToString[Min[c["Users"],batch+c["BatchSize"]-1]]]],
 {batch,1,c["Users"],c["BatchSize"]}];
 HBridge[{"finalize","--users",ToString[c["Users"]],"--seed",ToString[c["Seed"]]}];
 HJSON[HPath["outputs","metrics","generation.json"],<|"users"->c["Users"],"seed"->c["Seed"],"sessions"->sid,"events"->eid,"transactions"->tid,"generator"->"Wolfram Language"|>];
];
