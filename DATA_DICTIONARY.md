# Project Horizon 数据字典

Project Horizon 是虚构游戏。仓库内所有用户级与事件级数据均为作品集演示而合成，不使用专有、保密或真实玩家数据。

日期为模拟中的游戏日历日期，按 UTC 定义但不携带时区信息，范围为 2026-01-01 至 2026-06-29（含首尾）。相对 Day 0 为注册日，金额单位为 USD。活跃用户每日观察到 1–3 次会话，当日总分钟数拆分为正值；不将缺失事实填补为活跃。

| 表名 | 粒度与主键 | 字段及含义 |
|---|---|---|
| users | 每名玩家一行；user_id | register_date：注册日；market：CN/JP/KR/US/DE；acquisition_channel：获客渠道；campaign：获客活动；device：PC/iOS/Android；platform：desktop/mobile；age_bucket：年龄组；latent_player_archetype：生成审计用潜在玩家类型；acquisition_quality：生成审计用获客质量 |
| sessions | 每次实际会话一行；session_id | user_id、session_date；session_number：用户全生命周期累计会话序号；session_minutes >0；device；fps_quality_bucket：1 差 / 2 中 / 3 好；crash_flag：0/1 |
| progression | user_id + event_date | chapter：状态转移后已完成的最高章节；level=12 在成功与失败当日均标识第三章关卡；tutorial_completed/core_loop_unlocked：累计 0/1 状态；boss_attempts/boss_failures：当日增量 |
| gameplay_events | event_id | user_id、event_time、event_type、event_value；chapter_complete 的值为已完成章节；boss_attempt 的值为当日尝试次数；时间戳体现日内顺序 |
| monetization | transaction_id | user_id、transaction_date、product_type；amount_usd：非负 numeric(12,2) 金额 |
| acquisition | 每名玩家一行；user_id | market、channel、campaign、creative；acquisition_date 与注册日一致 |
| content_exposure | user_id + date + content_id | content_type、content_id；exposed、clicked 为 0/1；仅在活跃日观察触达，因此存在选择偏差 |
| run_metadata | key | 生成数量、种子、生成器来源及状态 |

生成机制中的潜在输入（参与度、消费、社交、技能及内容匹配）不作为分析预测变量。users 中保存的 latent_player_archetype 与 acquisition_quality 仅用于生成审计，在两种语言的模型设计矩阵中均排除。

KPI 口径：DAU 为当日去重活跃人数；WAU/MAU 为含当日在内的滚动 7/30 个日期去重人数。New 为注册当日活跃；Returned 为间隔 >=7 日后的当前会话；Retained 为其余非新注册活跃用户。New Users 为注册人数。D7 核心循环解锁率 / 引导完成率使用成熟 D7 队列和 D0–D7 事件。D1/D7/D30 为对应日期当日留存，各用独立成熟分母。Return Rate 为 Patch2 Day120–Day126 回流人数除以 Day106 前注册且 Day106–Day119 无活跃的人数。付费转化为生命周期内曾付费人数 / 全部用户；ARPU 与 ARPPU 使用完整观察期收入。

流失：仅纳入完整观察至 D30 的用户；预测特征为 D0–D7（含首尾），当且仅当 D22–D30（含首尾）无活跃时 churn_30=1。模型类别编码使用固定类别并删除一个基准类别；标准化参数仅在训练队列拟合。max_feature_day 仅用于审计，不进入模型。

分群在 Day179 互斥，优先级依次为：New & Unactivated、Returning、High Value、Healthy New、At Risk（沉默 7 日）、Highly Engaged Non-Payers（最近28日活跃至少10日）、Core Engaged。快照分群的历史队列留存比较为描述性结果，使用了相对于历史的未来信息。D7 模型风险分数另行形成运营候选名单。

漏斗：使用成熟 D7 玩家，六个累计核心阶段依次为 Register → Tutorial Start → Tutorial Complete → Core Unlock → Ch2 → Ch3。stage_type 区分 core 与 optional。Activity 和 Social 分别使用第三章完成人数为分母，事件必须在 D0–D7 内观察到；可选阶段不纳入最大核心步骤损失结论。

进度为每日快照：每个 user_id + 日期仅一行，boss_attempts/boss_failures 为当日增量，与会话次数无关。首领战诊断按 level 分组，不按转移后已完成的 chapter 分组。每日状态转移与游戏事件只执行一次。session_number 在用户全部生命周期会话中递增。崩溃标记分配给发生崩溃的活跃日第一场会话；当日是否发生任何崩溃与会话崩溃率使用不同分母。

实验 A：首次第12级尝试定义触达，按用户 1:1 随机分配。主要完成窗口为触达当日至第 +3 个日历日。基线分母为完整随访的首次触达用户，不按是否通关筛选。以注册日为起点的 D7/D14 留存次要指标各自使用成熟队列；关卡窗口成熟不要求注册 D30 成熟。B 使用第30日当日留存；C 使用返回后 D0–D6 的不同活跃日期数。

合成校准区间是机制设计的宽松护栏，不是行业基准。特征相关性诊断用于避免将相关参与度变量写成彼此独立的洞察。
