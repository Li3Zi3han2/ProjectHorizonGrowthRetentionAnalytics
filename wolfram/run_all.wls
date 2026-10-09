(* Headless primary entrypoint. --users 20000 --fast; --analyze skips generation. *)
Begin["Horizon`"];
$HRoot=DirectoryName[DirectoryName[$InputFileName]];
SetDirectory[$HRoot];
$CharacterEncoding="UTF8";
Scan[Get[FileNameJoin[{$HRoot,"wolfram",#<>".wl"}]]&, {"Config","Database","GenerateData","DataQuality","KPI","Retention","Funnel","Churn","Segmentation","Reactivation","ExperimentDesign","Visualization","Calibration","Report","Diagnostics"}];
$HC=HConfig[];
If[!StringQ[Environment["HORIZON_USERS"]]&&!MemberQ[System`$ScriptCommandLine,"--users"],$HC["Users"]=$HC["FastUsers"]];
If[MemberQ[System`$ScriptCommandLine,"--fast"],$HC["Users"]=$HC["FastUsers"]];
With[{p=Flatten[Position[System`$ScriptCommandLine,"--users"]]},If[Length[p]>0,$HC["Users"]=ToExpression[System`$ScriptCommandLine[[First[p]+1]]]]];
Scan[If[!DirectoryQ[HPath@@#],CreateDirectory[HPath@@#,CreateIntermediateDirectories->True]]&,{{"outputs","metrics"},{"outputs","tables"},{"outputs","models"},{"outputs","figures","wolfram"},{"outputs","figures","python"},{"outputs","parity"},{"outputs","report"}}];
$HM=<||>;HLog["Wolfram primary pipeline users="<>ToString[$HC["Users"]]];
(* Dataset and mode validation are coordinated by python_src.runner. *)
If[!MemberQ[System`$ScriptCommandLine,"--analyze"],HGenerate[$HC]];
$HDB=HConnect[];HQuality[];HLog["KPI"];HKPI[];HLog["Retention"];HRetention[];HLog["Funnel"];HFunnel[];HLog["Segmentation"];HSegments[];HReactivation[];HLog["Churn models"];HChurn[];HExperiments[];HCalibration[];HDiagnostics[];HVisualize[];HReport[];
DatabaseLink`CloseSQLConnection[$HDB];HLog["Primary pipeline complete"];End[];Exit[0];
