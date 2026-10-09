# Project Horizon — 游戏用户增长与留存分析

Project Horizon 是一个基于 200,000 名合成玩家、180 天行为数据构建的游戏数据分析作品集，覆盖留存、主线漏斗、流失风险、用户分群、回流分析和 A/B 实验设计。

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
| 成熟队列留存 | D1 / D7 / D30：**32.06% / 17.01% / 10.44%** |
| 付费 | 曾付费用户比例 **3.32%**；用户平均收入 **0.42 美元** |
| 核心进度 | 核心循环→第二章损失 **28.09%**；第二章→第三章损失 **27.36%**，转化率 72.64% |
| 关卡尝试 | 第12级首领战失败率 **62.67%**，分母为尝试次数 |
| 设备差异 | Android D7 留存比 PC 低 **3.30 个百分点** |
| 模型比较 | Logistic ROC-AUC **0.6840**；非线性模型 **0.6843**。Logistic PR-AUC 0.7701，Brier 0.2161 |
| 风险排序 | 风险最高10%用户的流失集中度为 **1.44×**，覆盖 **14.41%** 的目标窗口流失用户 |
| 沉默用户回流 | 68,635 人中 10,140 人回流，回流率 **14.77%**；返回后 D0–D6 平均活跃 2.55 个不同日期 |

- 第二章前后两个相邻步骤的损失接近，第12级又有直接失败记录，因此优先安排关卡实验。
- 非线性模型的 ROC-AUC 只高 0.000295，实际区分能力几乎没有变化，因此保留更容易解释的 Logistic 作为排序基线。
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
| 第12级首领战优化 | 首次尝试时 | 随后四个日历日内完成第三章 | 151,582 / 70.10% | 5,133 |
| 高风险用户扶持 | 第7日风险最高10%用户 | 第30日当日留存 | 4,087 / 3.74% | 850 |
| 回流内容导航 | 沉默14日后实际回流时 | 回流后 D0–D6 活跃日期数 | 10,140 / 2.55 天 | 235 |

三项方案均为实验设计，并未执行；MDE 和样本量是规划参数，不是已观察到的提升。

## 数据与验证

本次已验证数据包含 **200,000 名用户、180 天行为、2,419,602 次会话、3,957,854 条游戏行为事件和 8,916 笔交易**。

默认双引擎流程执行 pytest、Wolfram 自测及 Python 笔记本。历史正式 Wolfram / Python 一致性检查通过 1,601 项统计与特征检查、22 项模型与结论检查；正式 Fast / Full 证书位于 `outputs/validation/`，仅证明其记录的源码 fingerprint 和执行时间。

- [一致性报告](outputs/parity/wolfram_python_parity.md) · [最终发布验证](outputs/validation/final_release.json)
- [数据字典](DATA_DICTIONARY.md) · [分析边界](LIMITATIONS.md)
- [Wolfram 笔记本](wolfram/AnalysisWalkthrough.nb) · [已执行的 Python 笔记本](notebooks/python_analysis_walkthrough.ipynb)

## 项目结构

```text
Project-Horizon/
├─ portfolio/      # 作品集与图表
├─ sql/            # 指标、特征、标签和实验 SQL
├─ wolfram/        # 主实现
├─ python_src/     # 独立复算与验证
├─ notebooks/      # 分析演示
├─ tests/          # 自动化测试
├─ outputs/        # 小型、可审计结果
└─ tools/          # 发布与本地辅助工具
```

[项目说明](PROJECT_SPEC.md) · [SQL](sql/) · [Wolfram 源码](wolfram/) · [Python 源码](python_src/) · [测试](tests/)

## 复现

### 优先路径：没有 Wolfram 的 Python 全流程

需要 Python 3.11+、PostgreSQL 15+ 和 Python 依赖；Windows 主入口使用 PowerShell 7.x。Wolfram 是可选依赖。Python-only 真实生成合成事实并写入 PostgreSQL，再计算 KPI、成熟队列留存、漏斗、关卡诊断、分群、流失模型、回流、实验样本量、图表、Markdown/PDF 作品集和可执行 Notebook。

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.\tools\start_local_db.ps1

# 在项目内的本地 cluster 创建新的专用数据库；这一步只在首次执行。
createdb -w -h 127.0.0.1 -p 55432 -U horizon project_horizon_python
$env:HORIZON_DB_NAME='project_horizon_python'
$env:HORIZON_DB_SCHEMA='python_fast'
.\run_all.ps1 -Fast -PythonOnly

# Full 使用另一个 schema，保留 Fast 数据。
$env:HORIZON_DB_SCHEMA='python_full'
.\run_all.ps1 -Full -PythonOnly
```

Helper 初始化或复用项目内 `.local/pgdata`，默认只监听 `127.0.0.1:55432`，创建 `horizon` 用户和 `project_horizon` 数据库；只在 `.env` 不存在时创建配置，保留已有 `.env`。已有配置指向其他实例时，先核对连接设置；上述 createdb 命令针对默认本地 cluster，自定义 helper 端口时同时修改连接参数。trust 认证只用于本地合成数据开发，不用于生产。

所有运行写入独立的 `outputs/runs/<run_id>/`：其中 `run.json` 记录阶段、数据/源码哈希和产物清单，`outputs/validation/certificate.json` 声明认证范围，`portfolio/` 包含本次图表和 Markdown/PDF，`notebooks/` 包含本次执行记录。`.local/runs/` 保存同一运行索引。仓库已有作品集与历史 Fast/Full 证书不会被新运行覆盖。

Fast 为 20,000 用户，Full 为 200,000 用户，模拟均为 180 天；Full 模型非线性训练仍采用原有 30,000 样本上限。建议先完成 Fast。资源估计：Full 数据及审计产物需要数 GB 空间，分析建议至少 8 GB RAM；耗时依 CPU/数据库配置变化，实测结果见本轮验收报告。Full 不再依赖历史双引擎 Fast 证书。

### 已有 PostgreSQL / Linux / macOS

在已有实例上创建专用空数据库，配置 [.env.example](.env.example) 中的 host、port、database、user、password。环境变量优先于 `.env`；schema 默认是 `horizon`，可用 `HORIZON_DB_SCHEMA` 选择隔离目标。不要覆盖已有 `.env`；仅在文件不存在时复制模板。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# 仅在 .env 不存在时复制，然后编辑实际连接信息。
test -f .env || cp .env.example .env
export HORIZON_DB_SCHEMA=python_fast
bash ./run_all.sh --fast --python-only
export HORIZON_DB_SCHEMA=python_full
bash ./run_all.sh --full --python-only
```

Unix 不提供自动安装或启动 PostgreSQL 的 helper，需先准备数据库；Shell 和 PowerShell 委托同一个 Python 调度器。跨平台测试范围在验收报告中明确区分，Windows 上的 Git Bash 测试不等同于原生 Linux/macOS 集成测试。

### 三组参数与阶段边界

| 维度 | Windows | Unix | 规则 |
|---|---|---|---|
| 规模 | `-Fast` / `-Full` | `--fast` / `--full` | 必须且只能选择一个 |
| 分析引擎 | `-PythonOnly` / `-WolframOnly` | `--python-only` / `--wolfram-only` | 互斥；不选则双引擎 |
| 阶段 | `-GenerateOnly` / `-AnalyzeOnly` | `--generate-only` / `--analyze-only` | 互斥；不选则生成后分析 |

```powershell
.\run_all.ps1 -Fast -PythonOnly                 # Python 生成、分析、验证
.\run_all.ps1 -Full -PythonOnly                 # 正式规模 Python 全流程
.\run_all.ps1 -Full -AnalyzeOnly -PythonOnly    # 只读已有有效 Full 数据
.\run_all.ps1 -Fast                            # Wolfram 生成一份数据，双引擎独立分析及 parity
.\run_all.ps1 -Full -WolframOnly                # Wolfram 生成、分析及自检，无 Python 分析
.\run_all.ps1 -Fast -GenerateOnly               # 只生成及校验，无分析
.\run_all.ps1 -Fast -GenerateOnly -PythonOnly   # 特例：忽略语言参数，明确提示实际生成器
```

`GenerateOnly` 是唯一语言参数例外：实际启动 Wolfram 内核并检查授权，可用则优先 Wolfram，否则 Python 生成，并显示：**Python 生成的数据不保证与 Wolfram 生成的数据逐条相同，亦不能预先保证由不同数据得出的数值结论一致；但必须满足同一项目的数据契约及独立可复现要求。** 运行中生成器出错不会自动再次生成。

非 GenerateOnly 的 PythonOnly 从不检查/启动 Wolfram；WolframOnly 和默认双引擎在 Wolfram 不可用时失败，给出 Python-only 命令。Wolfram 可选安装须提供已授权的 Wolfram Language 13+ 和可执行的 `wolframscript`，可用 `HORIZON_WOLFRAM_KERNEL` 指定内核。Wolfram-only 仍使用公共 Python 调度、COPY 和展示适配器，需要公共 Python 依赖，但不运行 Python 指标或模型分析。

AnalyzeOnly 在运行前检查完成标记、Fast/Full 规模、schema/约束、所有事实表的内容指纹；不建数、不修复、不替换数据，允许生成语言与分析语言不同。旧数据没有完成 manifest 时会失败，需要显式迁移，不能把旧输出当作当前证据。

生成默认拒绝覆盖已有目标 schema。推荐选择新数据库或新 schema。只有明确设置 `HORIZON_ALLOW_REPLACE=1` 才允许替换，且旧 schema 会原子重命名为可恢复的 `<schema>_backup_<id>`；新生成先在 `<schema>_build_<id>` 完成，失败不会发布不完整数据。不要把该授权用于用户主数据库。历史 schema 和运行目录不自动删除；确认不再需要后，可由使用者显式清理对应目标。

无参数、规模冲突/重复、语言冲突、阶段冲突都会非零退出，且在任何数据库操作前失败。查看 Unix 帮助：`bash ./run_all.sh --help`；Windows 帮助：`Get-Help .\run_all.ps1 -Full`。这是对旧入口的兼容性变更：无参数不再默认为 Fast，`-Fast/-Full` 现在可以与 Only 组合；Fast/Full 本身仍包含生成和分析，只有 GenerateOnly 才仅生成。

### 数据、方法和认证的区别

Python 生成器按原 Wolfram 状态转移和业务概率实现，使用逐用户 NumPy RandomState MT19937，种子仍为 20261005。两种语言随机取样和分布算法不同，相同种子不表示逐行一致。数据 manifest 保存生成器、参数、版本、源码/配置指纹、表行数、约束和完整内容哈希；Fast/Full 的前 20,000 用户在同一 Python 生成器下应逐行一致。

Python-only PASS 要求本轮 Python 算法、数据库/产物完整性、独立 SQL 比对、模型数值和业务不变量、回归测试通过；Wolfram 和 parity 为 SKIPPED。Wolfram-only 具有自身通过范围。GenerateOnly 只认证数据。双引擎只有同一份输入、当次双方结果及 parity 通过才认证。测试中不适用的跨语言/发布项写明跳过原因，不把 SKIPPED 当 PASS；事务变异回归在解除分析锁后单独运行。

仓库展示的正式数字来自原 Wolfram 数据集，其原始内容指纹和公开聚合数值见 [正式数据基准](config/published_baseline.json)。独立 Python 合成数据可复现完整方法，不保证复现这些精确数字；同一原始数据的分析一致性与不同生成器的数据差异分别报告。历史证书仅证明其执行时的源码，不能证明当前源码或本次运行；模式通过也不代表 release-level 通过。

### 故障排查

- 连接超时/拒绝或无凭据：检查 PostgreSQL 服务、端口与 `.env`；无配置时默认尝试 `localhost:5432/project_horizon`，Python-only 也需要数据库。
- 目标 schema 已存在：保留数据，改用新 schema，或在理解备份和替换语义后显式授权。
- AnalyzeOnly 报规模/指纹/结构不匹配：选择正确数据集；不要手工改 manifest 哈希或用重生成掩盖错误。
- Python 依赖缺失：用 `.venv` 的 Python 安装 requirements；可用 `HORIZON_PYTHON` 显式指定解释器。
- 双引擎缺 Wolfram/授权：使用同规模的 PythonOnly，或配置有效授权；不会静默降级双引擎分析。
- 分析/测试失败：查看本轮 `run.json` 与对应阶段 `.log`，非零退出且不签发通过证书。

## 分析边界

这是合成数据作品集，生成机制本身包含预设假设。观察性差异、模型系数和版本前后变化均不等于因果效应；没有真实广告成本、LTV、ROI 或已经执行的干预结果。详细说明见 [LIMITATIONS.md](LIMITATIONS.md)。

当前仓库未指定开源许可证。

## 发布源码与作品集来源核验

当前源码指纹采用 horizon-source-v2-posix-ordinal-raw-bytes：按相对 POSIX 路径的区分大小写顺序，依次哈希路径 UTF-8 和文件原始字节。旧算法依赖 Path 的平台排序，Windows/POSIX 可能不同；旧证书保留历史含义。发布构建会在本地、发布树和独立 ZIP 解压树复算，并核验全部当前模式证书与同目录 dataset manifest。

作品集正文、流程图、测试数量和 Notebook 状态从本次运行证据生成；测试完成后刷新最终 Markdown。历史公开作品集与本轮模式输出分别记录。需要自行渲染 PDF 时，在执行前设置环境变量 HORIZON_PDF_MODE=manual；此时生成 Markdown/图片和带 Markdown 哈希的 render request，证书的 PDF 状态为 PENDING_USER_RENDER，不能解释成 PDF 已验收。未设置则仍自动从最终 Markdown 渲染。

### 解压后的依赖安装

ZIP不包含虚拟环境。先在解压目录创建 .venv，再用该环境的Python安装 requirements-lock.txt（锁定的验收依赖）或 requirements.txt，然后运行脚本；无需激活环境，入口优先使用该目录 .venv。HORIZON_PYTHON 若已设置则优先于 .venv，须确认它指向装好依赖的解释器。本轮已实际验证 Python 3.13.5 新建虚拟环境、从锁文件完整安装、默认 horizon schema/同名数据库用户和 Python Fast 全流程。缺依赖时入口给出选中的解释器及匹配的安装命令。
