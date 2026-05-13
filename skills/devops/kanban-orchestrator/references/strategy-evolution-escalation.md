# 三策略进化看板 — 结构性不可达升级协议

> 版本: 1.1.0 | 日期: 2026-05-13 夜间
> 适用看板: evo-a / evo-b / evo-c (活跃) + strat-a / strat-b / strat-c (已退役)

## 架构

```
每个策略独立看板（evo-a / evo-b / evo-c 或 strat-a / strat-b / strat-c）

正常进化循环:
  code-optimize → finance-backtest → reviewer-judge
       ↑                                    |
       └────────── 继续下一轮 ←──────────────┘
                          ↓ (结构性不可达检测触发)
                     research-escalate → code-refactor → finance-validate
```

## 结构性不可达判定标准

| 条件 | 判定 | 动作 |
|:--|:--|:--|
| 连续3轮年化改善 < 5% | 🔴 结构性瓶颈 | 升级research |
| 单轮年化下降 > 50% | 🔴 逻辑崩坏 | 立即升级research |
| 夏普 < 0.5 或 胜率 < 35% | 🔴 策略失效 | 升级research |
| 年化 < 0%（连续亏损） | 🔴 反向信号 | 升级research |
| finance worker 明确表示"结构性不可达" | 🔴 专家判断 | 立即升级research |
| 年化改善 5-20% | 🟡 边际改善 | 继续1轮后判断 |
| OOS验证失败（样本外年化<0） | 🔴 过拟合 | 升级research |

## Research 升级路径

### 阶段1: 诊断 (research-domain)
**任务模板**:
```
标题: {策略名}诊断-结构性不可达根因分析
assignee: research-domain
body:
  1. 读取当前策略代码和回测日志
  2. 找出性能断崖的具体改动点
  3. 评估当前结构的天花板
  4. 提出2-3个重构方向（含预估收益/风险）
  5. 产出诊断报告到 /home/pebynn/quant/research/{策略名}_diagnosis.md
```

### 阶段2: 重构 (code-domain, parent=阶段1)
**任务模板**:
```
标题: {策略名}重构-基于诊断实施方案
assignee: code-domain
body:
  1. 读取诊断报告
  2. 按推荐方向重构策略代码
  3. 增量修改，先跑基线验证
  4. 禁止：未来数据泄露、删除有效风控
```

### 阶段3: 验证 (finance-domain, parent=阶段2)
**任务模板**:
```
标题: {策略名}验证-重构后回测
assignee: finance-domain
body:
  1. 运行重构后策略回测
  2. 对比基线指标
  3. 年化>15% = 重构有效；8-15% = 边际；<8% = 失败
  4. 产出对比报告
```

## 验证后决策

| 重构结果 | 动作 |
|:--|:--|
| 年化 > 30%（显著改善） | 回归正常进化循环 |
| 年化 15-30%（有效改善） | 继续1-2轮正常进化 |
| 年化 8-15%（边际改善） | reviewer判断：继续进化 or 归档 |
| 年化 < 8%（失败） | 归档当前方向，考虑全新范式 or 标记放弃 |

## B+D 强制层（每次 kanban_create 必执行）

```bash
# Step 1: wrap
python3 ~/.hermes/scripts/bd_layer_enforce.py wrap \
  --domain <domain> --body "<body>" --title "<title>" --assignee <worker>

# Step 2: create with enriched_body
hermes kanban --board <board> create "<title>" --assignee <worker> --body "<enriched_body>"

# Step 3: set dependent tasks to todo
sqlite3 <board_db> "UPDATE tasks SET status='todo' WHERE id='<tid>';"

# Step 4: subscribe QQ Bot
hermes kanban --board <board> notify-subscribe --platform qqbot --chat-id A88D89D... <tid>
```

## 三策略当前状态 (2026-05-13 夜间)

| 策略 | 看板 | 状态 | 最新指标 | 判定 |
|:--|:--|:--|:--|:--|
| A 动量+资金流 | evo-a | R3全周期回测中 | 年化119.6%/胜率35.7%/MDD-54.6% | 待OOS验证 |
| B 事件驱动 | evo-b | R5止步 | 年化-12.67%/胜率0% | **不可达** |
| C 政策概念 | evo-c | R6审查中 | PolicyWeightEngine已接入 | 待评估 |

注: 旧三策略(动量截面/超跌反转/缠论二买)看板strat-a/b/c已退役，每日信号cron 0637e225e375仍在运行。

## 案例: 旧A策略OOS惨败 — IS过拟合 (2026-05-13) ⚠️ 看板strat-a已退役

- 旧策略A: 动量截面(多均线突破)，看板strat-a(已退役)

- 声称: IS年化1234-1392%，胜率66.1%
- OOS验证: 3周期全负(-38%/-75%/-71%)，IS真实年化仅14.85%
- 根因: 纯价量因子IS过拟合，paper noise清理后不影响结果
- 教训: IS指标完全不可信 → OOS必须作为策略验收强制门禁
- 后续: 策略A从零重启，IC优先(IC>0.05+ICIR>0.3才进回测)

## 案例: 旧B策略Leak-Plugging (2026-05-13) ⚠️ 看板strat-b已退役

- 旧策略B: 超跌反转，看板strat-b(已退役)

R1(38.31%)→R2(52.63%)，4项改动各自贡献:

| 改动 | 效果 | 诊断 |
|:--|:--|:--|
| SCORE_DECAY | 238笔, 均值+3517/笔 | 🆕 最成功: 替代rebalance主利润源 |
| MARKET_REGIME减半 | 下行保护+14.38pp, 上行仅-1.70pp | ✅ 不对称保护净+12.68pp |
| TIME_STOP 3d→2d/ret<-1% | 亏损-6692→-4490/笔 | ✅ 更早砍仓释放资金 |
| TRAILING_STOP -6%→-3% | 持平 | ⚠️ -3%过紧, 建议-5% |

天花板确认: 1x杠杆反转≈50-55%，距300%有结构鸿沟。

## 案例: B事件驱动策略 — PEAD信号A股证伪 (2026-05-13)

- 策略: 事件驱动(PEAD财报漂移+资金确认)，看板evo-b
- 进化: R1→R5，共14个任务(code→finance→reviewer × 5轮)
- R3基线移除未来函数后: 12笔交易全部亏损
- R5加入政策权重增强: 年化-12.67%/胜率0%/6笔全败
- AKShare全线离线致政策权重中性(1.0)无法生效
- 根因: PEAD公告前量比信号在2026年A股被证伪——强意外事件(SUE≥2.0)也无法转化收益
- 判定: **不可达**。连续4轮(R2/R3/R4/R5)未改善超10%
- 处置: 执行不可达收尾协议 → evo-b看板删除 → 编排器缩减为双策略。策略代码保留供alpha分量参考。
- 产出了: output/round5_b_audit.json

## 全周期回测任务强制写法 (2026-05-13)

finance worker倾向于跑短周期(当前年/数月)而非指令的完整多年区间。task body必须同时包含：

```
强制要求:
1. 回测区间: 2021-01-01 到 2025-12-31 (完整5年)
2. 禁止只跑2026年数据。若代码中日期硬编码,先修改再运行。
3. 验证方法: 回测完成后检查trading_days应该>1000(5年约1210个交易日)
4. 分别报告各年度子区间指标
```

关键: 指定具体区间 + 禁止短周期 + 可量化验证标准(trading_days>1000)。纯文本"跑全周期"不足以阻止工人投机。

## 案例: B策略升级 (2026-05-13，旧B-超跌反转，看板strat-b)

- 触发: R9 56%→R12 8.5%，finance worker断言"300%结构性不可达"
- 诊断任务: t_dde304d6 (research-domain)
- 重构任务: t_af45af1b (code-domain, parent of 诊断)
- 验证任务: t_6aab8afa (finance-domain, parent of 重构)
- 看板: strat-b

## 不可达收尾协议 (2026-05-13)

reviewer宣告不可达后，执行以下6步清理序列：

```
1. 读取最终审核结果确认判定
   hermes kanban --board <board> show <reviewer_task_id>

2. 暂停编排器cron（避免在清理期间自动创建新任务）
   cronjob(action='pause', job_id='<evo_orchestrator_cron_id>')

3. 删除看板目录
   rm -rf ~/.hermes/kanban/boards/<board_slug>

4. 保存教训到域lessons文件
   echo "## YYYY-MM-DD: <策略名>宣告不可达 ..." >> ~/.hermes/lessons/<domain>.md

5. 更新编排器cron prompt移除该策略
   cronjob(action='update', job_id='<cron_id>', prompt='<new_prompt>')
   → 将 "三策略" 改为 "双策略"，删除对应看板引用

6. 恢复编排器cron
   cronjob(action='resume', job_id='<cron_id>')

7. 验证: hermes kanban boards list 确认看板已消失
```

策略代码保留在quant/strategies/<strategy_dir>/，供后续作为辅助因子分量参考。

**真实案例**: evo-b (B事件驱动PEAD) R5宣告不可达 → 上述6步执行完毕，看板消失，编排器从三策略缩减为双策略(evo-a+evo-c)。耗时<2分钟。
