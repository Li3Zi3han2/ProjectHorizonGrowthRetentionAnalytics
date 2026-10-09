Begin["Horizon`"];
$HRoot=DirectoryName[DirectoryName[$InputFileName]];
Get[FileNameJoin[{$HRoot,"wolfram","Config.wl"}]];
Get[FileNameJoin[{$HRoot,"wolfram","GenerateData.wl"}]];
Get[FileNameJoin[{$HRoot,"wolfram","Churn.wl"}]];
toy=HEvaluate[{0.,0.,1.,1.},{.1,.8,.9,.2}];
HAssert[toy["confusion_matrix"]=={{1,1},{1,1}}&&toy["precision"]==.5&&toy["recall"]==.5&&toy["f1"]==.5,"machine-real label classification regression"];
SeedRandom[20261005];a=$HSim[0,.6,.5,.5,.5,.5,1,1,.6,RandomReal[1.,{180,13}]];
(* An independently repeated seeded random matrix must produce identical history. *)
SeedRandom[20261005];b=$HSim[0,.6,.5,.5,.5,.5,1,1,.6,RandomReal[1.,{180,13}]];
SeedRandom[20261006];c=$HSim[0,.6,.5,.5,.5,.5,1,1,.6,RandomReal[1.,{180,13}]];
active=Select[a,#[[7]]>0&];
nb=Get[HPath["wolfram","AnalysisWalkthrough.nb"]];
inputs=Cases[nb,Cell[BoxData[code_],"Input",___]:>code,Infinity];
(* NotebookDirectory needs a front end; substitute the portable root for headless QA. *)
Do[If[i==1,root=With[{v=Environment["HORIZON_ARTIFACT_ROOT"]},If[StringQ[v]&&v!="",v,$HRoot]];summary=Import[HPath["outputs","executive_summary.json"],"RawJSON"],HAssert[Quiet[Check[ToExpression[inputs[[i]],StandardForm];True,False]],"notebook input cell "<>ToString[i]]],{i,Length[inputs]}];
r=<|"same_seed_same_simulation"->SameQ[a,b],"different_seed_changes_simulation"->!SameQ[a,c],"no_progression_regression"->Min[Differences[active[[All,2]]]]>=0,"positive_session_minutes"->Min[active[[All,7]]]>0,"notebook_input_cells_executed"->Length[inputs]|>;
HAssert[And@@Take[Values[r],4],"seeded state transition self-test"];
HJSON[HPath["outputs","metrics","wolfram_selftest.json"],r];Print[r];End[];Exit[0];
