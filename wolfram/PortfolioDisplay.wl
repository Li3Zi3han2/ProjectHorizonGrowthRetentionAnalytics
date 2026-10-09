(* Read-only portfolio display helpers. Inputs are validated tables and scores. *)
$HDisplayBlue=ColorData[97][1];
$HRetentionPalette=Function[v,Blend[{White,ColorData[97][1]},v]];
HDisplayNumber[v_,places_:2]:=ToString[NumberForm[N[v],{12,places},NumberPadding->{"","0"}]];
HDisplayPercent[v_]:=HDisplayNumber[100 v]<>"%";
HDisplayCount[v_]:=ToString[NumberForm[v,DigitBlock->3,NumberSeparator->","]];
HDisplayTitle[title_,note_]:=Column[{Style[title,16],Style[note,13,GrayLevel[.35]]},Alignment->Center,Spacings->.4];

HDisplayRetention[curve_]:=Module[{pts,marks},
 pts=Lookup[#,{"d","rate"}]&/@curve;marks=Select[pts,MemberQ[{1,7,30},First[#]]&];
 HLine[pts,"成熟队列的当日留存随注册时间下降","距注册日的天数","当日留存率",ImageSize->900,AspectRatio->.38,PlotRange->{{1,30},{0,.4}},FrameTicks->{{HPercentTicks[.4],None},{Automatic,None}},Epilog->{
  $HDisplayBlue,PointSize[.009],Point[marks],
  Text[Style["第1日 "<>HDisplayPercent[marks[[1,2]]],14],{2,marks[[1,2]]+.034},{-1,0}],
  Text[Style["第7日 "<>HDisplayPercent[marks[[2,2]]],14],{8,marks[[2,2]]+.030},{-1,0}],
  Text[Style["第30日 "<>HDisplayPercent[marks[[3,2]]],14],{29,marks[[3,2]]+.025},{1,0}]}]
];

HDisplayDevice[rows_]:=Module[{r=SortBy[rows,#["rate"]&],n,pts,gap},
 n=Length[r];pts=MapIndexed[{#1["rate"],n+1-First[#2]}&,r];gap=Max[pts[[All,1]]]-Min[pts[[All,1]]];
 Graphics[{
  GrayLevel[.9],Table[Line[{{0,j},{.24,j}}],{j,n}],
  MapIndexed[Function[{row,idx},{If[First[idx]==1,$HDisplayBlue,GrayLevel[.55]],PointSize[.014],Point[pts[[First[idx]]]],Text[Style[HDisplayPercent[row["rate"]],15],pts[[First[idx]]]+{.007,0},{-1,0}]}],r]},
  Frame->{{True,False},{True,False}},Axes->False,FrameTicks->{{MapIndexed[{n+1-First[#2],#1["category"]}&,r],None},{HPercentTicks[.25,.05],None}},FrameLabel->{"第7日当日留存率",None},
  PlotLabel->HDisplayTitle["Android 留存最低，PC 高出 "<>HDisplayNumber[100 gap]<>" 个百分点","仅成熟队列；设备差异为观察性证据"],PlotRange->{{0,.25},{.5,n+.5}},ImageSize->900,AspectRatio->.28,ImagePadding->{{110,35},{60,70}},BaseStyle->$HFigureStyle,Background->White]
];

HDisplayFunnel[rows_]:=Module[{n=Length[rows],primitives},
 primitives=MapIndexed[Function[{r,idx},With[{y=n+1-First[idx]},
  {Directive[$HDisplayBlue,Opacity[.72]],Rectangle[{0,y-.23},{r["n"],y+.23}],
   Black,Text[Lookup[$HStageNames,r["name"]],{-8500,y},{1,0}],
   Text[HDisplayCount[r["n"]],{224000,y}],
   Text[Style[If[First[idx]==1,"—",HDisplayPercent[r["dropoff"]]],If[First[idx]>=5,$HDisplayBlue,GrayLevel[.35]],If[First[idx]>=5,Bold,Plain]],{298000,y}]}]],rows];
 Graphics[{primitives,GrayLevel[.35],Text["核心主线阶段",{-8500,n+.85},{1,0}],Text["累计到达人数",{224000,n+.85}],Text["较前阶段损失",{298000,n+.85}],Text[Style["条带从零起；注册后第0–7日累计进度",13],{125000,.1}]},
  PlotRange->{{-110000,336000},{-.2,n+1.25}},PlotLabel->HDisplayTitle["第二章前后形成相邻、规模接近的双重摩擦","仅核心主线；活动与社交另列采用率"],ImageSize->950,AspectRatio->.45,BaseStyle->$HFigureStyle,Background->White,ImagePadding->{{15,15},{10,65}}]
];

HDisplayGate[gate_]:=Graphics[{
 GrayLevel[.9],Line[{{0,1},{1,1}}],$HDisplayBlue,AbsoluteThickness[2],Line[{{0,1},{gate["failure_rate"],1}}],PointSize[.015],Point[{gate["failure_rate"],1}],
 Text[Style[HDisplayPercent[gate["failure_rate"]],18,Bold],{gate["failure_rate"],1.22}],
 Black,Text[Style[HDisplayCount[gate["failures"]]<>" 次失败 / "<>HDisplayCount[gate["attempts"]]<>" 次尝试（次数口径）",14],{.5,.68}]},
 Frame->{{False,False},{True,False}},Axes->False,FrameTicks->{{None,None},{HPercentTicks[1,.2],None}},FrameLabel->{"尝试失败率",None},
 PlotLabel->HDisplayTitle["第12级首领战提供直接摩擦证据，优先进入实验","现有诊断仅覆盖第12级，不能据此判断跨等级峰值"],PlotRange->{{0,1},{.5,1.43}},ImageSize->900,AspectRatio->.22,ImagePadding->{{35,35},{60,70}},BaseStyle->$HFigureStyle,Background->White];

HDisplayCalibration[cal_]:=HLine[{cal,{{0,0},{1,1}}},"Logistic 风险概率校准：分组预测与实际比例","分组平均预测流失概率","分组实际流失比例",PlotStyle->{$HDisplayBlue,Directive[GrayLevel[.6],Dashed]},PlotMarkers->{Automatic,None},PlotLegends->Placed[{"Logistic 概率分组","理想校准"},Below],PlotRange->{{0,1},{0,1}},AspectRatio->.48,ImageSize->900,FrameTicks->{{HPercentTicks[1,.2],None},{HPercentTicks[1,.2],None}}];

HDisplayCoefficients[rows_]:=Module[{r=SortBy[rows,#["coefficient"]&],n,pts,b},
 n=Length[r];pts=MapIndexed[{#1["coefficient"],n+1-First[#2]}&,r];b=1.40 Max[Abs[pts[[All,1]]]];
 Graphics[{Directive[GrayLevel[.65],Dashed],Line[{{0,.5},{0,n+.5}}],
  Map[Function[pt,{Directive[$HDisplayBlue,AbsoluteThickness[1.5],Dashing[{}]],Line[{{0,pt[[2]]},pt}],PointSize[.010],Point[pt],Black,Text[Style[HDisplayNumber[First[pt]],15],pt+{Sign[First[pt]] .060,0},{-Sign[First[pt]],0}]}],pts]},
  Frame->{{True,False},{True,False}},Axes->False,FrameTicks->{{MapIndexed[{n+1-First[#2],Lookup[$HFeatureNames,#1["feature"]]}&,r],None},{Automatic,None}},FrameLabel->{"标准化特征的条件系数（0 为中心）",None},
  PlotLabel->HDisplayTitle["Logistic 条件预测信号：系数按方向与大小排序","展示绝对值最大的10项；相关参与度特征应联合解释"],PlotRange->{{-b,b},{.5,n+.5}},ImageSize->950,AspectRatio->.56,ImagePadding->{{260,50},{72,75}},BaseStyle->{FontFamily->$HFigureFont,FontSize->17},Background->White]
];

HDisplayDeciles[rows_,ev_]:=Module[{pts=Lookup[#,{"decile","churn_30"}]&/@SortBy[rows,#["decile"]&]},
 HLine[pts,"风险排序与实际流失集中度呈清晰的有序关系","风险十分位（1 为最高风险）","流失率相对总体的倍数",ImageSize->900,AspectRatio->.38,PlotMarkers->Automatic,PlotStyle->$HDisplayBlue,PlotRange->{{.6,10.4},{0,1.65}},FrameTicks->{{Automatic,None},{Table[{i,i},{i,10}],None}},
  Epilog->{Directive[GrayLevel[.6],Dashed],Line[{{.6,1},{10.4,1}}],Black,Text[Style["总体 = 1",13,GrayLevel[.4]],{9.4,1.07}],Text[Style["最高风险10%："<>HDisplayNumber[ev["lift_at_10pct"]]<>"×\n捕获流失用户 "<>HDisplayPercent[ev["capture_at_10pct"]],14],{5.5,1.43},{-1,0}]}]
];

HDisplaySegments[rows_]:=Module[{r=Reverse[SortBy[rows,#["active_days28"]&]],n,total,primitives},
 n=Length[r];total=Total[Lookup[r,"n"]];
 primitives=MapIndexed[Function[{row,idx},With[{y=n+1-First[idx]},
  {GrayLevel[.90],Line[{{0,y},{12,y}}],$HDisplayBlue,PointSize[.010],Point[{row["active_days28"],y}],Black,
   Text[Lookup[$HSegmentNames,row["segment"]],{-.6,y},{1,0}],
   Text[Style[HDisplayNumber[row["active_days28"]],13],{row["active_days28"]+.38,y},{-1,0}],
   Text[HDisplayPercent[row["n"]/total]<>" / "<>HDisplayCount[row["n"]],{17.2,y}]}]],r];
 Graphics[{primitives,GrayLevel[.4],Text["期末分群",{-.6,n+.9},{1,0}],Text["近28日平均活跃天数",{6,n+.9}],Text["占比 / 人数",{17.2,n+.9}],
  Line[{{0,.38},{12,.38}}],Table[{Line[{{v,.38},{v,.25}}],Text[Style[ToString[v],13],{v,0}]},{v,0,12,3}]},
  PlotRange->{{-6.4,21.4},{-.35,n+1.3}},PlotLabel->HDisplayTitle["分群同时看规模与行为，避免只按人数判断价值","期末互斥快照；均值是描述，运营方向仍需检验"],ImageSize->950,AspectRatio->.43,BaseStyle->$HFigureStyle,Background->White,ImagePadding->{{15,15},{15,65}}]
];

HDisplayReturn[r_]:=Graphics[{
 GrayLevel[.8],Line[{{.33,.50},{.33,.94}}],Line[{{.67,.50},{.67,.94}}],Black,
 Text[Style["沉默观察池",14],{.16,.90}],Text[Style[HDisplayCount[r["eligible"]]<>" 人",21,$HDisplayBlue],{.16,.73}],Text[Style["更新前14日无活跃",13],{.16,.56}],
 Text[Style["更新后七日内回流",14],{.50,.90}],Text[Style[HDisplayCount[r["returned"]]<>" 人",21,$HDisplayBlue],{.50,.73}],Text[Style["回流率 "<>HDisplayPercent[r["returned"]/r["eligible"]],14],{.50,.56}],
 Text[Style["回流后七日持续活跃",14],{.84,.90}],Text[Style[HDisplayNumber[r["post_return_days7"]]<>" 天",21,$HDisplayBlue],{.84,.73}],Text[Style["第0–6日平均活跃日期数",13],{.84,.56}],
 Directive[GrayLevel[.5],AbsoluteThickness[1.5]],Arrow[{{.07,.38},{.96,.38}}],
 Line[{{.07,.34},{.07,.42}}],Line[{{.38,.34},{.38,.42}}],Line[{{.69,.34},{.69,.42}}],
 Black,Text[Style["先确认沉默资格",13],{.21,.27}],Text[Style["再观察首次回流",13],{.53,.27}],Text[Style["从回流日起计七日",13],{.83,.27}],
 Text[Style["观察性结果：没有随机对照，不能归因为版本收益",13,GrayLevel[.35]],{.50,.08}]},
 PlotRange->{{0,1},{0,1}},PlotLabel->"回流规模之外，还要观察回流后的活跃持续性",ImageSize->950,AspectRatio->.31,BaseStyle->$HFigureStyle,Background->White,ImagePadding->{{20,20},{15,50}}];

HDisplayDAU[daily_]:=Module[{base,stack,colors,labels},
 base=Lookup[daily,#]&/@{"new_active","retained","returned"};stack=Accumulate[base];colors=ColorData[97]/@Range[3];labels={"当日新注册","存量：距上次活跃不足七日","回流：间隔至少七日"};
 HAssert[stack[[3]]==Lookup[daily,"dau"],"display DAU components sum to existing DAU"];
 Labeled[HLine[stack,"DAU 随存量累积增长，回流贡献另行识别","模拟日","当日活跃用户数（人）",DataRange->{0,Length[daily]-1},Filling->{1->Axis,2->{1},3->{2}},FillingStyle->Thread[Range[3]->(Directive[#,Opacity[.65]]&/@colors)],PlotStyle->colors,PlotRange->{{0,Length[daily]-1},{0,All}},AspectRatio->.37,ImageSize->900],SwatchLegend[colors,labels,LegendLayout->"Row",LabelStyle->Directive[FontFamily->$HFigureFont,FontSize->13]],Bottom]
];
