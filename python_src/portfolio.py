"""Presentation from validated artifacts only; never writes analysis metrics or PDFs."""
import json
import shutil
import pandas as pd
import xml.etree.ElementTree as ET
from .config import ROOT, OUT, ARTIFACT_ROOT

PORTFOLIO_PRINT_STYLE = """---
puppeteer:
  format: A4
  preferCSSPageSize: true
  timeout: 3000
---

<style>
@page { size: A4; margin: 14mm 13mm 15mm 13mm; }
img[alt="Project Horizon GitHub"] { width: 30mm; height: 30mm; }
@media print {
  body, .markdown-preview.markdown-preview {
    font-family: "Microsoft YaHei", "Noto Sans CJK SC", "Source Han Sans SC", sans-serif;
    color: #222; background: white; font-size: 11pt; line-height: 1.6;
  }
  .markdown-preview.markdown-preview { padding: 0; width: auto; }
  h1 { font-size: 21pt; margin: 0 0 7mm; }
  h2 { font-size: 15pt; margin: 6mm 0 3mm; }
  h3 { font-size: 12pt; }
  h1, h2, h3 { break-after: avoid; page-break-after: avoid; }
  p, li { orphans: 3; widows: 3; }
  p { margin: 0 0 3mm; }
  img, table, pre, blockquote, .mermaid, .mermaid-container {
    break-inside: avoid; page-break-inside: avoid;
  }
  img { max-width: 100%; height: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 9.8pt; margin: 3mm 0; }
  thead { display: table-header-group; }
  tr { break-inside: avoid; page-break-inside: avoid; }
  th, td { padding: 4px 6px; vertical-align: top; }
  blockquote { margin: 3mm 0; padding: 1mm 3mm; }
  blockquote p { margin: 1mm 0; }
  .mermaid, .mermaid-container { overflow: visible !important; text-align: center; }
  .mermaid svg, .mermaid-container svg {
    max-width: 100% !important; width: auto !important; height: 100mm !important;
    overflow: visible !important;
    display: block; margin: 0 auto;
  }
}
</style>
"""

SEGMENTS = {
    "At-Risk Users": ("近期沉默用户", "判断沉默原因，再检验轻量触达"),
    "Core Engaged Users": ("核心活跃用户", "保持内容节奏，观察体验稳定性"),
    "Healthy New Users": ("健康新用户", "跟进进度，避免过早商业触达"),
    "High-Value Users": ("高价值用户", "优先处理体验问题"),
    "Highly Engaged Non-Payers": ("高活跃未付费用户", "检验内容与付费需求匹配"),
    "New & Unactivated": ("新注册未激活用户", "检验引导与核心循环入口"),
    "Returning Users": ("回流用户", "检验个性化内容导航"),
}

def read_json(name):
    return json.loads((OUT/name).read_text(encoding="utf-8"))

def auc_comparison(delta):
    direction = f"低 {abs(delta):.6f}" if delta < 0 else f"高 {delta:.6f}"
    if abs(delta) < .01:
        return f"非线性模型的 ROC-AUC {direction}，实际区分能力几乎没有变化，因此保留更容易解释的 Logistic 作为排序基线。"
    return f"非线性模型的 ROC-AUC {direction}；应结合模型指标、校准与运营预算评估。"

def execution_provenance(engine, dual):
    manifest=read_json('dataset_manifest.json')
    scope='dual_engine' if dual else 'python_only' if engine=='python' else 'wolfram_only'
    run_path=ARTIFACT_ROOT/'run.json'
    run=json.loads(run_path.read_text(encoding='utf8')) if run_path.exists() else {}
    run_id=run.get('run_id', manifest['run_id'])
    generator=manifest['generator']
    analyzers='Wolfram 与 Python' if dual else engine.title()
    overview=f'本次数据由 {generator} 生成，PostgreSQL 是唯一事实源；本次分析器为 {analyzers}。认证范围为 {scope}，运行 ID 为 {run_id}。'
    title='本次双引擎分析与数据血缘' if dual else '本次独立分析与数据血缘'
    branches=('    B --> C["Wolfram 分析"]\n    B --> D["Python 分析"]\n    C --> E["当次 parity 与自检"]\n    D --> E' if dual else f'    B --> C["{engine.title()} 分析"]\n    C --> E["本次独立自检；parity SKIPPED"]')
    flow=f'```mermaid\nflowchart TD\n    A["{generator} 生成数据"] --> B["PostgreSQL 保存事实"]\n{branches}\n    E --> F["本次图表、报告与实验方案"]\n```'
    xml=OUT/'metrics/pytest.xml'
    passed=skipped=None
    if xml.exists():
        suites=list(ET.parse(xml).getroot().iter('testsuite'))
        assert suites and all(int(s.get('failures',0))==int(s.get('errors',0))==0 for s in suites)
        skipped=sum(int(s.get('skipped',0)) for s in suites)
        passed=sum(int(s.get('tests',0))-int(s.get('skipped',0)) for s in suites)
    tests=f'本次 pytest 通过 {passed} 项、跳过 {skipped} 项。' if passed is not None else '本次 pytest 尚未执行；测试结果待最终验证。'
    py=OUT/'metrics/notebook_execution.json';wl=OUT/'metrics/wolfram_selftest.json'
    py_done=py.exists() and (dual or engine=='python') and read_json('metrics/notebook_execution.json').get('status')=='PASS'
    wl_done=wl.exists() and (dual or engine=='wolfram') and read_json('metrics/wolfram_selftest.json').get('notebook_input_cells_executed',0)>0
    notebooks=f'Python Notebook：{"已执行" if py_done else "尚未执行" if dual or engine=="python" else "SKIPPED"}；Wolfram 自检与原生 Notebook：{"已执行" if wl_done else "尚未执行" if dual or engine=="wolfram" else "SKIPPED"}。'
    parity=read_json('parity/status.json')
    assert parity['status']==('PASS' if dual else 'SKIPPED')
    parity_text=(f'当次 parity PASS：{parity["descriptive_checks"]:,} 项统计与特征检查、{parity["model_checks"]} 项模型与结论检查。' if dual else '当次跨语言 parity 为 SKIPPED；本次未执行双引擎交叉验证。')
    certificate=OUT/'validation/certificate.json'
    if certificate.exists():
        c=read_json('validation/certificate.json')
        assert c['scope']==scope and c['dataset_sha256']==manifest['dataset_sha256'] and c['run_id']==run_id
        assert c['validation']['tests']==passed and c['validation']['skipped']==skipped
    return overview,title,flow,tests+notebooks+parity_text

def generate_presentation(engine='wolfram',dual=True):
    s = read_json("executive_summary.json")
    e = read_json(f"models/{engine}_evaluation.json")
    parity = read_json("parity/status.json")
    assert parity["status"] == ("PASS" if dual else "SKIPPED"), "Presentation requires current mode evidence"
    g = read_json("metrics/generation.json")
    fd = read_json("validation/feature_diagnostics.json")
    f = pd.read_csv(OUT/"tables/funnel.csv")
    core = f.loc[f.dimension.eq("overall") & f.stage_type.eq("core")].set_index("name")
    optional = f.loc[f.dimension.eq("overall") & f.stage_type.eq("optional")].set_index("name")
    wall = pd.read_csv(OUT/"tables/progression_diagnosis.csv").set_index("level").loc[12]
    ex = pd.read_csv(OUT/"tables/experiment_design.csv").set_index("experiment")
    perf = pd.read_csv(OUT/"tables/device_performance.csv").set_index(["device", "period"])
    pre, post = perf.loc[("Android", "pre_patch1")], perf.loc[("Android", "post_patch1")]
    ret = pd.read_csv(OUT/"tables/retention_breakdown.csv")
    channels = ret.loc[ret.dimension.eq("channel") & ret.d.eq(7)].sort_values("rate")
    cn = {"organic":"自然流量","video_ads":"视频广告","creator":"内容创作者","referral":"好友推荐","store_feature":"商店推荐","cross_promo":"交叉推广"}
    channel_rows = "\n".join(f"| {cn[r.category]} | {r.rate:.2%} |" for r in channels.itertuples())
    seg = pd.read_csv(OUT/"tables/segments.csv")
    high_value_n = int(seg.loc[seg.segment.eq("High-Value Users"), "n"].iloc[0])
    segment_rows = "\n".join(
        f"| {SEGMENTS[r.segment][0]} | {r.n:,}（{r.n / s['users']:.2%}） | {r.active_days28:.2f} 天；{r.payer_rate:.2%} 曾付费 | {SEGMENTS[r.segment][1]} |"
        for r in seg.sort_values("n", ascending=False).itertuples())
    last = pd.read_csv(OUT/"tables/daily_kpis.csv").iloc[-1]
    d1, d2 = core.loc["chapter_2", "dropoff"], core.loc["chapter_3", "dropoff"]
    delta = e["nonlinear"]["roc_auc"] - e["logistic"]["roc_auc"]
    model_source = ('下表为 Wolfram 主实现的时间测试结果。Python 独立复算；非线性算法不同，按预先声明的指标差异与名单重合规则验收。' if dual else f'下表为本次 {engine.title()} 独立分析的时间测试结果；跨语言 parity 为 SKIPPED。')
    model_narrative = auc_comparison(delta)
    overview,provenance_title,flow,test_summary=execution_provenance(engine,dual)
    model_rows = "\n".join(
        f"| {name} | {e[key]['roc_auc']:.4f} | {e[key]['pr_auc']:.4f} | {e[key]['brier']:.4f} | {e[key]['lift_at_10pct']:.2f}× | {e[key]['capture_at_10pct']:.2%} |"
        for name, key in [("Logistic","logistic"),("非线性提升树","nonlinear")])
    text = f"""{PORTFOLIO_PRINT_STYLE}
# Project Horizon｜游戏用户增长与留存分析

## 1. 项目概览

Project Horizon 是虚构的跨平台免费动作角色扮演游戏。全部 {s['users']:,} 位用户及 {s['simulation_days']} 天行为均为合成数据，用于展示分析方法；没有真实玩家数据、企业项目经历或真实商业提升。

项目从留存和主线漏斗出发，用注册后前八日行为预测后续沉默，并据此安排三个随机实验方案。{overview}下文数字来自本次配置，种子为 {s['seed']}。

## 2. 最值得先试的三个问题

| 优先问题 | 看到的结果 | 下一步 |
|---|---|---|
| 优先实验第12级首领战 | 核心循环→第二章损失 {d1:.2%}，第二章→第三章损失 {d2:.2%}；第12级失败率 {s['chapter3_gate_failure_rate']:.2%} | 首次尝试时比较难度、资源或引导调整 |
| 验证 Android 性能优化 | Android 第7日留存最低，比 PC 低 {s['device_d7_gap']*100:.2f} 个百分点 | 按市场和版本分层，随机比较优化效果 |
| 优先触达高风险用户 | 最高风险10%流失集中度 {s['lift_at_10pct']:.2f}×，覆盖 {s['capture_at_10pct']:.2%} 的流失用户 | 留出随机对照；回流用户另做导航实验 |

这些结果用来决定下一步先试什么，相关改动尚未测得收益。

## 3. {provenance_title}

实际生成 {g['sessions']:,} 次会话、{g['events']:,} 条行为事件和 {g['transactions']:,} 笔交易。七张关系表连接用户、获客、会话、进度、行为、交易与内容触达；CSV 只作传输及审计产物。

{flow}

{test_summary}主外键、日期、会话序号、时长、缺失与进度单调性均纳入质量检查。

每个留存观察日分别筛选已有完整观察窗口的用户，称为成熟样本。模型用注册后第0至第7日的信息，预测第22至第30日是否沉默；标准化只拟合训练集，潜在变量和未来行为不进入特征。

## 4. 第7日留存为 {s['overall_d7']:.2%}，后期 DAU 以存量用户为主

| 指标 | 实际结果 | 口径 |
|---|---:|---|
| 第1日留存 | {s['overall_d1']:.2%} | 第1日有活跃，成熟分母 |
| 第7日留存 | {s['overall_d7']:.2%} | 第7日有活跃，成熟分母 |
| 第30日留存 | {s['overall_d30']:.2%} | 第30日有活跃，成熟分母 |
| 前八日核心循环解锁 | {s['activation_rate']:.2%} | 第0至第7日累计解锁 |
| 曾付费用户比例 | {s['payer_conversion']:.2%} | 观测期内首次付费 |
| 用户平均收入 | {s['arpu']:.2f} 美元 | 收入除以全部注册用户 |

![注册后留存曲线](assets/01_retention_curve.png)

按注册周检查队列差异，各观察日使用各自的成熟分母。热图空白表示窗口尚未成熟，并非零留存。

![按注册周观察留存：空白为未成熟](assets/02_cohort_heatmap.png)

末日 DAU、WAU、MAU 为 **{int(last.dau):,}、{int(last.wau):,}、{int(last.mau):,} 人**。面积图总高度等于 DAU；从下到上依次为当日新注册、距上次活跃不足七日的存量，以及间隔至少七日后的回流用户。

![每日活跃构成](assets/11_dau_composition.png)

核心循环累计解锁不等于第7日当日留存。晚注册用户付费暴露期更短，曾付费比例也不等于成熟180日队列转化率。

## 5. Android 第7日留存最低，先检验性能优化

**PC 比 Android 高 {s['device_d7_gap']*100:.2f} 个百分点。** 各设备的实际留存率如下。

![设备第7日留存](assets/03_device_d7.png)

首个版本更新前后，Android 早期活跃用户日崩溃率由 {pre.crash_rate:.2%} 降至 {post.crash_rate:.2%}，流畅度等级均值由 {pre.mean_fps:.2f} 升至 {post.mean_fps:.2f}。等级是合成指标，不是每秒帧数。版本前后没有随机对照；下一步在 Android 用户中随机比较性能优化，并按市场和版本分层。

| 渠道 | 第7日留存 |
|---|---:|
{channel_rows}

渠道间留存差异也受到市场、设备与注册时间影响。这里没有广告成本或随机对照，无法据此推算投放回报。

## 6. 第二章前后都有明显损失，先试第12级首领战

| 核心循环→第二章损失 | 第二章→第三章损失 | 第12级尝试失败率 |
|---:|---:|---:|
| **{d1:.2%}** | **{d2:.2%}** | **{wall.failure_rate:.2%}** |

成熟第7日的 {int(core.loc['Register','n']):,} 位用户中，{int(core.loc['core_loop_unlock','n']):,} 人解锁核心循环，{int(core.loc['chapter_2','n']):,} 人完成第二章，{int(core.loc['chapter_3','n']):,} 人完成第三章。两个相邻步骤的损失接近；第二章→第三章转化为 {s['chapter3_completion_given_chapter2']:.2%}。图中人数是前八日累计达到各阶段的人数，右列损失以紧邻的前一阶段为分母。

![核心主线阶段人数与条件损失](assets/04_core_funnel.png)

![第12级首领战尝试失败率](assets/05_level12_friction.png)

第12级的 {int(wall.attempts):,} 次尝试中，{int(wall.failures):,} 次失败，失败率为 {wall.failure_rate:.2%}，因此先把该首领战作为实验点。可能原因包括难度、资源不足和引导不清。分母是尝试次数，同一用户可以多次尝试；现有诊断仅覆盖第12级，不能比较跨等级峰值。

活动与社交是可选功能，以第三章完成者为分母，采用率分别为 {optional.loc['activity_enter','conversion']:.2%} 和 {optional.loc['social_interaction','conversion']:.2%}，不纳入核心进度损失比较。

## 7. 只用前八日行为，预测第22–30日沉默

流失标签是注册后第22至第30日均无活跃，与“第30日当天未活跃”不同。特征为第0至第7日的参与、进度、性能和付费行为，只纳入完整观察到第30日的用户。

| 时间划分 | 注册日范围 | 用户数 |
|---|---|---:|
| 训练集 | 第0–89日 | {e['train_n']:,} |
| 验证集 | 第90–119日 | {e['validation_n']:,} |
| 测试集 | 第120–149日 | {e['test_n']:,} |

按时间切分更接近面对新队列的部署情境。测试集不调参；非线性模型按预先设定限制使用训练期最早的 {e['nonlinear_train_n']:,} 位用户。

## 8. 风险排序有用，复杂模型增益有限

{model_source}

| 模型 | ROC-AUC ↑ | PR-AUC ↑ | Brier ↓ | 前10%集中度 | 前10%捕获率 |
|---|---:|---:|---:|---:|---:|
{model_rows}

**{model_narrative}** ↑ 表示越高越好，↓ 表示越低越好；概率是否准确还要看校准。

![Logistic 分组预测概率与实际流失比例](assets/06_model_calibration.png)

校准图沿用现有时间测试集预测，按预测概率区间分组。点越接近虚线，分组预测越接近实际比例；空区间不绘点。Brier 衡量整体概率误差，上线前仍需验证新队列校准与漂移。

![Logistic条件预测信号](assets/07_logistic_coefficients.png)

单个系数表示**控制其他特征后的条件预测关联**。会话次数与活跃天数相关系数为 {fd['session_active_day_correlation']:.3f}；{fd['fraction_users_multiple_sessions']:.2%} 的成熟用户会话数多于活跃日数。会话、活跃天数、总时长和平均会话时长应作为一组参与度指标理解。会话次数的正系数不能解释为“多玩会导致流失”，也不能代替单变量趋势。

| 触达预算 | 最高风险组流失集中度 | 捕获目标窗口流失用户 |
|---:|---:|---:|
| **10%** | **{s['lift_at_10pct']:.2f}×** | **{s['capture_at_10pct']:.2%}** |

![风险十分位点线图：总体集中度为1](assets/08_risk_decile.png)

最高风险组的实际流失率为总体的 {s['lift_at_10pct']:.2f} 倍，说明排序有用；高风险不等于可被挽回。运营名单按预算确定。阈值0.5下精确率 {e['logistic']['precision']:.2%}、召回率 {e['logistic']['recall']:.2%}、F1 {e['logistic']['f1']:.4f} 仅作分类诊断，与图中十分位排序不同。

## 9. 分群用于安排服务顺序，回流还要看后续活跃

![七类分群的规模与近28日平均活跃天数](assets/09_segments.png)

| 期末分群 | 人数（占比） | 行为特征 | 可尝试的服务 |
|---|---:|---|---|
{segment_rows}

行为特征中的天数是近28日平均活跃日期数，付费比例为观测期内曾付费比例。分群按固定优先级互斥。“近期沉默用户”是最近七日未活跃的规则，与第7日模型名单不同；期末分群回看留存有后验选择，只适合描述。高价值群仅{high_value_n:,}人，行动优先级不能只看群体人数。

第二次版本更新前十四日无活跃且更早注册的用户共 {s['reactivation_eligible']:,} 人，七日内 {s['reactivation_count']:,} 人回流，回流率 {s['reactivation_rate']:.2%}。返回后第0至第6日平均活跃 {s['post_return_active_days']:.2f} 个不同日期。该观察池与上表期末“回流用户”的快照口径不同，人数无需相同。

![沉默观察池、回流规模与返回后七日活跃](assets/10_reactivation.png)

这 {s['reactivation_rate']:.2%} 的回流混合了自然回访、时间变化和版本更新的影响，不能直接归因于版本。回流导航实验在用户实际返回时随机分组。

## 10. 三项方案都在实际触发时随机分组

```mermaid
flowchart TD
    A["达到实验资格"] --> B["用户级 1:1 随机分组"]
    B --> C["处理组"]
    B --> D["对照组"]
    C --> E["完成固定观察窗口"]
    D --> E
    E --> F["比较主要指标与护栏指标"]
    F --> G["按预设规则判断"]
```

| 实验 | 主要指标及窗口 | 历史人数 | 基线 | 规划 MDE | 每组人数 |
|---|---|---:|---:|---:|---:|
| A：关卡 | 首次尝试当日至第3日，完成第三章 | {int(ex.loc['A','eligible_n']):,} | {ex.loc['A','baseline']:.2%} | +{ex.loc['A','mde']*100:.1f} 个百分点 | {int(ex.loc['A','per_arm']):,} |
| B：扶持 | 第30日当日留存 | {int(ex.loc['B','eligible_n']):,} | {ex.loc['B','baseline']:.2%} | +{ex.loc['B','mde']*100:.1f} 个百分点 | {int(ex.loc['B','per_arm']):,} |
| C：导航 | 返回后第0–6日活跃日期数 | {int(ex.loc['C','eligible_n']):,} | {ex.loc['C','baseline']:.2f} 天 | +{ex.loc['C','mde']:.1f} 天 | {int(ex.loc['C','per_arm']):,} |

A 包含当日及之后三日，共四个日历日期；历史基线包含所有完整随访的首次尝试用户，不因通关筛选，其中 {int(ex.loc['A','completed_n']):,} 人在窗口内完成。表中 MDE 均为规划假设，历史资格人数不等于未来招募保证。

> **A｜第12级首领战优化**
>
> 玩家首次尝试时随机分组，一组采用{ex.loc['A','treatment']}，另一组保持原体验。比较随后四个日历日期内的第三章完成率，资格不按是否通关筛选。另看注册后第7、14日成熟留存，以及崩溃、时长、付费和后续进度。

> **B｜第7日高风险用户扶持**
>
> 第7日风险最高的10%用户随机分组，处理组安排{ex.loc['B','treatment']}。主要比较第30日当日留存，次要比较第22至第30日是否活跃；监控崩溃、付费和退出触达。

> **C｜实际回流时的内容导航**
>
> 连续十四日沉默的用户实际返回时随机分组，处理组使用{ex.loc['C','treatment']}。主要比较返回后第0至第6日活跃日期数，并观察崩溃、再次沉默和付费。均值样本量近似上线前需模拟检验。

均按用户1:1分配、双侧显著性水平0.05、统计功效0.80规划。锁定主要指标、分层、完整随访及停止规则；先完成固定观察窗口，再按预设规则判断。**实验尚未执行，没有测得因果效应。**

## 11. 分析边界与复现说明

- 合成机制编码用户异质性、生命周期衰减、性能摩擦和关卡门槛，不能外推为真实市场事实。
- 引导、社交与内容触达有参与度自选择，相关不代表因果。
- 版本与回流比较有时间、队列混杂，缺少随机对照。
- 晚注册用户存在观察期截断；当日留存、窗口活跃、累计激活分别解读。
- 相关参与度特征限制单系数解释；模型需前瞻校准、漂移与干预响应验证。
- 多会话与经济被简化，没有广告成本、网络干扰或真实投资回报。
- 留存区间仅反映二项抽样误差，不覆盖生成机制不确定性；多维分组属探索分析。
- 样本量依赖独立用户与固定窗口假设，不构成已实现商业提升。

### 完整项目与复现资料

完整源码、数据字典、分析边界、跨语言一致性验证、实验设计及复现说明均公开在 GitHub：

**[Project Horizon 项目仓库](https://github.com/Li3Zi3han2/ProjectHorizonGrowthRetentionAnalytics)**

[![Project Horizon GitHub](assets/github_qr.png)](https://github.com/Li3Zi3han2/ProjectHorizonGrowthRetentionAnalytics)

本作品 PDF 可独立阅读；源码、验证记录与复现材料不在求职附件中重复打包。
"""
    (ARTIFACT_ROOT/"portfolio").mkdir(parents=True,exist_ok=True)
    (ARTIFACT_ROOT/'portfolio/assets').mkdir(parents=True,exist_ok=True)
    if ARTIFACT_ROOT!=ROOT:
        shutil.copy2(ROOT/'portfolio/assets/github_qr.png',ARTIFACT_ROOT/'portfolio/assets/github_qr.png')
    (ARTIFACT_ROOT/"portfolio/Project_Horizon_Portfolio.md").write_text(text, encoding="utf-8")
    if ARTIFACT_ROOT==ROOT and dual: write_readme(s, e, g, ex, d1, d2, fd, delta)

def write_readme(s, e, g, ex, d1, d2, fd, delta):
    # Keep the maintained Windows / Unix setup and mode documentation intact.
    current = (ROOT/"README.md").read_text(encoding="utf-8")
    marker = "## 项目结构"
    if marker not in current:
        raise ValueError("README must contain the maintained 项目结构 / 复现 sections")
    model_narrative = auc_comparison(delta)
    validation_text=(f"当前 Wolfram / Python 一致性检查通过 {s['parity'].get('descriptive_checks',0):,} 项统计与特征检查、{s['parity'].get('model_checks',0)} 项模型与结论检查；证书仅证明其记录的源码 fingerprint 和执行时间。" if s['parity']['status']=='PASS' else '本次为单引擎分析；独立验证结果以运行报告为准，跨语言 parity 为 SKIPPED，不声明双引擎通过。')
    text = f"""# Project Horizon — 游戏用户增长与留存分析

Project Horizon 是一个基于 {s['users']:,} 名合成玩家、{s['simulation_days']} 天行为数据构建的游戏数据分析作品集，覆盖留存、主线漏斗、流失风险、用户分群、回流分析和 A/B 实验设计。

所有用户、事件和商业结果均为合成数据，不包含真实玩家或企业数据，也不代表真实公司项目经历；实验方案尚未实际执行。

## 作品集

- [作品集（PDF）](portfolio/Project_Horizon_Portfolio.pdf)
- [作品集（Markdown）](portfolio/Project_Horizon_Portfolio.md)

快速了解项目请先看 PDF；它是 Markdown 源文件的派生阅读版本。README 重点说明项目结构、方法和复现方式。

## 这个项目展示了什么

- 按成熟队列计算 D1 / D7 / D30 留存，并观察每日活跃构成。
- 比较核心漏斗的相邻步骤损失，用关卡尝试和失败记录选择实验点。
- 用早期行为预测后续沉默风险，按注册时间验证模型，避免未来信息泄漏。
- 根据近期行为划分用户群，分析沉默用户回流后的活跃。
- 为关卡优化、用户扶持和回流导航设计 A/B 实验，规划样本量与统计功效。
- 在 PostgreSQL 同一事实源下，由 Wolfram / Python 独立复算，并运行自动化测试。

## 关键结果

| 分析 | 结果 |
|---|---|
| 成熟队列留存 | D1 / D7 / D30：**{s['overall_d1']:.2%} / {s['overall_d7']:.2%} / {s['overall_d30']:.2%}** |
| 付费 | 曾付费用户比例 **{s['payer_conversion']:.2%}**；用户平均收入 **{s['arpu']:.2f} 美元** |
| 核心进度 | 核心循环→第二章损失 **{d1:.2%}**；第二章→第三章损失 **{d2:.2%}**，转化率 {s['chapter3_completion_given_chapter2']:.2%} |
| 关卡尝试 | 第12级首领战失败率 **{s['chapter3_gate_failure_rate']:.2%}**，分母为尝试次数 |
| 设备差异 | Android D7 留存比 PC 低 **{s['device_d7_gap']*100:.2f} 个百分点** |
| 模型比较 | Logistic ROC-AUC **{e['logistic']['roc_auc']:.4f}**；非线性模型 **{e['nonlinear']['roc_auc']:.4f}**。Logistic PR-AUC {e['logistic']['pr_auc']:.4f}，Brier {e['logistic']['brier']:.4f} |
| 风险排序 | 风险最高10%用户的流失集中度为 **{s['lift_at_10pct']:.2f}×**，覆盖 **{s['capture_at_10pct']:.2%}** 的目标窗口流失用户 |
| 沉默用户回流 | {s['reactivation_eligible']:,} 人中 {s['reactivation_count']:,} 人回流，回流率 **{s['reactivation_rate']:.2%}**；返回后 D0–D6 平均活跃 {s['post_return_active_days']:.2f} 个不同日期 |

- 第二章前后两个相邻步骤的损失接近，第12级又有直接失败记录，因此优先安排关卡实验。
- {model_narrative}
- 回流和版本前后差异是观察结果，不能据此声称干预带来了提升。

## 分析设计

| 技术 | 职责 |
|---|---|
| Wolfram Language | 合成数据生成与主分析 |
| PostgreSQL | 唯一事实源，保存关系表 |
| Python | 从同一数据库独立复算关键指标与模型结果 |

各留存观察日分别使用已完成相应观察窗口的用户作为分母。流失模型仅使用 D0–D7 行为，预测 D22–D30 是否持续无活跃，只纳入完整观察到第30日的用户。

训练、验证、测试集按注册时间切分：第0–89日 / 第90–119日 / 第120–149日。特征不含潜在变量或未来行为；标准化仅在训练集拟合。0.5 阈值只作分类诊断，实际运营名单按预算进行风险排序。

## 三个待验证实验

详细口径见 [实验设计](outputs/tables/experiment_design.csv)。历史人数与基线用于样本量规划。

| 实验 | 随机时点 | 主要指标 | 历史人数 / 基线 | 每组样本量 |
|---|---|---|---:|---:|
| 第12级首领战优化 | 首次尝试时 | 随后四个日历日内完成第三章 | {int(ex.loc['A','eligible_n']):,} / {ex.loc['A','baseline']:.2%} | {int(ex.loc['A','per_arm']):,} |
| 高风险用户扶持 | 第7日风险最高10%用户 | 第30日当日留存 | {int(ex.loc['B','eligible_n']):,} / {ex.loc['B','baseline']:.2%} | {int(ex.loc['B','per_arm']):,} |
| 回流内容导航 | 沉默14日后实际回流时 | 回流后 D0–D6 活跃日期数 | {s['reactivation_count']:,} / {s['post_return_active_days']:.2f} 天 | {int(ex.loc['C','per_arm']):,} |

三项方案均为实验设计，并未执行；MDE 和样本量是规划参数，不是已观察到的提升。

## 数据与验证

本次已验证数据包含 **{s['users']:,} 名用户、{s['simulation_days']} 天行为、{g['sessions']:,} 次会话、{g['events']:,} 条游戏行为事件和 {g['transactions']:,} 笔交易**。

{validation_text}

- [一致性报告](outputs/parity/wolfram_python_parity.md) · [最终发布验证](outputs/validation/final_release.json)
- [数据字典](DATA_DICTIONARY.md) · [分析边界](LIMITATIONS.md)
- [Wolfram 笔记本](wolfram/AnalysisWalkthrough.nb) · [已执行的 Python 笔记本](notebooks/python_analysis_walkthrough.ipynb)

"""
    (ROOT/"README.md").write_text(text + marker + current.split(marker, 1)[1], encoding="utf-8")

if __name__ == "__main__":
    generate_presentation()
