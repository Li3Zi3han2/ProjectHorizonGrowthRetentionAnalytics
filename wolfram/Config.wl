(* Horizon namespace is shared by the modular packages loaded by run_all.wls. *)
HConfig::usage="HConfig[] loads portable project defaults and environment overrides.";
HConfig[]:=Module[{c=Get[FileNameJoin[{$HRoot,"config","config.wl"}]],v},
 v=Environment["HORIZON_USERS"];If[StringQ[v]&&StringLength[v]>0,c["Users"]=ToExpression[v]];c];
HPath[parts__]:=Module[{p={parts},out=Environment["HORIZON_OUTPUT_DIR"],art=Environment["HORIZON_ARTIFACT_ROOT"]},Which[First[p]=="outputs"&&StringQ[out]&&out!="",FileNameJoin[Prepend[Rest[p],out]],MemberQ[{"portfolio","notebooks"},First[p]]&&StringQ[art]&&art!="",FileNameJoin[Prepend[p,art]],p=={"wolfram","AnalysisWalkthrough.nb"}&&StringQ[art]&&art!="",FileNameJoin[Prepend[p,art]],True,FileNameJoin[Prepend[p,$HRoot]]]];
HJSON[path_,a_]:=Export[path,a,"RawJSON"];
HCSV[path_,rows_List]:=If[Length[rows]>0,Export[path,Prepend[Values/@rows,Keys[First[rows]]],"CSV"],Export[path,{},"CSV"]];
HAssert[condition_,message_]:=If[!TrueQ[condition],Print["FAILED: ",message];Exit[1]];
HLog[s_]:=Print[DateString[{"Hour",":","Minute",":","Second"}]," ",s];
