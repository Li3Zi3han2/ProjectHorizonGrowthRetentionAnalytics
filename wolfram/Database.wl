HConnect::usage="HConnect[] opens PostgreSQL using environment-provided credentials.";
Needs["DatabaseLink`"];
HEnv[k_,default_]:=With[{v=Environment[k]},If[StringQ[v]&&v!="",v,default]];
HConnect[]:=Module[{c},c=DatabaseLink`OpenSQLConnection[DatabaseLink`JDBC["PostgreSQL",HEnv["HORIZON_DB_HOST","localhost"]<>":"<>HEnv["HORIZON_DB_PORT","5432"]<>"/"<>HEnv["HORIZON_DB_NAME","project_horizon"]],"Username"->HEnv["HORIZON_DB_USER",""],"Password"->HEnv["HORIZON_DB_PASSWORD",""],"Timeout"->600];HAssert[MatchQ[c,_DatabaseLink`SQLConnection],"PostgreSQL connection"];c];
HQuery[q_String]:=Module[{r=DatabaseLink`SQLExecute[$HDB,StringReplace[q,"horizon."->(HEnv["HORIZON_DB_SCHEMA","horizon"]<>".")],"ShowColumnHeadings"->True]},HAssert[ListQ[r]&&Length[r]>0,"SQL query failed"];AssociationThread[First[r],#]&/@Rest[r]];
HSQLFile[name_]:=HQuery[Import[HPath["sql",name],"Text"]];
HBridge[args_List]:=Module[{r=RunProcess[Join[{HEnv["HORIZON_PYTHON","python"],"-m","python_src.transport"},args],All]},If[r["StandardOutput"]!="",Print[r["StandardOutput"]]];HAssert[r["ExitCode"]==0,r["StandardError"]];r];
