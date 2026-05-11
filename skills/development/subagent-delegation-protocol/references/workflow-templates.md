# 工作流模板库 — Role Chain 完整定义

## 模板1: 公众号复盘发布（高风险—全链）

```
触发: 每日15:30 cron / 手动 "发复盘"
链: research-domain(Researcher) → writing-domain(Creator) → Reviewer → Synthesizer
role_chain.py --template publish-review --task "生成今日A股复盘"

Step 1 - Researcher (research-domain, v4-pro):
  产出: 结构化事实清单 (指数/板块/资金流/涨停池/涨跌家数)
  约束: 每个数字标注 [来源: xxx]，不分析不推荐

Step 2 - Creator (writing-domain, v4-flash):
  产出: 复盘文章初稿
  约束: 不采集新数据，禁bullet points，图表用 ![]() 语法

Step 3 - Reviewer (独立, v4-flash):
  产出: PASS/FAIL + 四维评分
  阻断: FAIL → 链终止，Synthesizer不可执行

Step 4 - Synthesizer (独立, v4-flash):
  产出: 公众号草稿箱文章
  前置: Reviewer必须PASS
```

## 模板2: 量化信号生成（高风险）

```
触发: 手动 "跑信号" / cron
链: research-domain → finance-domain → Reviewer
role_chain.py --template signal-review --task "生成今日量化信号"

Step 1 - Researcher (research-domain, v4-pro):
  产出: 全市场K线+资金流+技术指标

Step 2 - Creator (finance-domain, v4-pro):
  产出: 信号列表(代码+方向+置信度+因子)
  约束: 不引入Researcher未提供的指标

Step 3 - Reviewer (独立, v4-flash):
  阻断: 无数据支撑的信号→FAIL
```

## 模板3: 数据分析报告（中风险）

```
链: research-domain → [writing/finance-domain] → Reviewer → Synthesizer
条件: 仅结果需要外发时启用全链。内部使用→跳过Reviewer
```

## 模板4: 代码开发（中风险）

```
链: code-domain → (可选 Reviewer)
条件: 生产环境/核心管线脚本→启用Reviewer。日常开发→单agent
```

## 模板5: 日常维护（低风险）

```
单 domain agent，不启用任何链。
测判断: 产出不外发 + 无资金风险 + 可逆操作
```

## 决策树

```
任务
├─ 外发内容(公众号/消息推送)？      → 模板1 (全链 R→W→Rv→S)
├─ 交易信号/投资建议？              → 模板2 (R→F→Rv)
├─ 数据分析报告(外发)？             → 模板3 (R→[domain]→Rv→S)
├─ 数据分析(内部)？                 → 模板3 (R→[domain]，跳过Rv)
├─ 生产代码？                      → 模板4 (D→Rv)
├─ 开发代码？                      → 模板4 (D only)
└─ 日常维护？                      → 模板5 (单agent)
```
