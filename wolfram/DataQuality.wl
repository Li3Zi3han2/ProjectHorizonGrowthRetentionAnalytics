HQuality::usage="HQuality[] validates chronology and completeness against PostgreSQL.";
HQuality[]:=Module[{r=HSQLFile["01_data_quality.sql"],n},HCSV[HPath["outputs","tables","data_quality_summary.csv"],r];HAssert[Total[Lookup[r,"failures"]]==0,"data quality"];n=First[HQuery["SELECT count(*) n FROM horizon.users"]]["n"];HAssert[n==$HC["Users"],"user count"];r];
