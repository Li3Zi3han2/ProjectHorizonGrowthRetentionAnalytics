HSegments::usage="HSegments[] builds exclusive operations segments from facts.";
HSegments[]:=Module[{r=HSQLFile["07_segments.sql"]},Do[$HM["segment/"<>x["segment"]]=x["n"],{x,r}];HCSV[HPath["outputs","tables","segments.csv"],r];r];
