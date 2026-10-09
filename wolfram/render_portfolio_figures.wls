(* Only render validated outputs: no generation, training or metric updates. *)
Begin["Horizon`"];
$HRoot=DirectoryName[DirectoryName[$InputFileName]];
Get[FileNameJoin[{$HRoot,"wolfram","Config.wl"}]];
$CharacterEncoding="UTF8";
Get[FileNameJoin[{$HRoot,"wolfram","Visualization.wl"}]];
status=Import[HPath["outputs","parity","status.json"],"RawJSON"];
HAssert[status["status"]=="PASS","validated inputs required"];
If[!DirectoryQ[HPath["outputs","figures","wolfram"]],CreateDirectory[HPath["outputs","figures","wolfram"],CreateIntermediateDirectories->True]];
HAssert[Length[DownValues[HVisualize]]>0,"visualization source loaded"];
HVisualize[];
Print["Rendered 19 Wolfram figures; 11 portfolio assets. Metrics unchanged."];
End[];Exit[0];
