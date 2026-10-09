(* Generation only; dataset completion and atomic publication are coordinated externally. *)
Begin["Horizon`"];
$HRoot=DirectoryName[DirectoryName[$InputFileName]];SetDirectory[$HRoot];$CharacterEncoding="UTF8";
Scan[Get[FileNameJoin[{$HRoot,"wolfram",#<>".wl"}]]&, {"Config","Database","GenerateData"}];
$HC=HConfig[];HGenerate[$HC];End[];Exit[0];
