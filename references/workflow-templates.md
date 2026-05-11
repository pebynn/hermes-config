# 工作流模板库

> 常见跨域任务固化为可复用模板。每个模板定义 Role 链 + 输入输出契约 + 启用条件。

## 模板1: 公众号复盘发布（高风险）

```
触发: 每日15:30 cron / 手动 "发复盘"
条件: 交易日 + data_guard PASS

链: Researcher → Writer → Reviewer → Synthesizer

Researcher (v4-pro, stock-sdk+mysql):
  输入: "采集今日A股数据"
  产出: 结构化事实清单 (指数/板块/资金流/涨停池/涨跌家数)
  源: stock-sdk-mcp + Sina
  验证: 每个数字有来源标注

Writer (v4-flash, file+terminal):
  输入: Researcher 产出 + 域风格规范(公众号排版)
  产出: 复盘文章初稿
  约束: 不采集新数据，禁 bullet points，图表用 ![]() 语法

Reviewer (v4-flash, file):
  输入: Writer 初稿 + data_guard.py 门禁
  产出: PASS/FAIL + 问题列表
  约束: 只审查不修改

Synthesizer (v4-flash, file+terminal):
  输入: Writer 初稿 + Reviewer PASS
  产出: 草稿箱文章
```

## 模板2: 量化信号生成（高风险）

```
触发: 手动 "跑信号" / cron
条件: data_guard PASS

链: Researcher → Analyst → Reviewer

Researcher (v4-pro, stock-sdk+mysql):
  产出: 全市场 K线+资金流+技术指标

Analyst (v4-pro, execute_code+file):
  输入: Researcher 产出
  产出: 信号列表 (代码+方向+置信度+因子组成)
  约束: 不引入 Researcher 未提供的指标

Reviewer (v4-flash, file):
  输入: Analyst 信号列表
  产出: PASS/FAIL + 回测验证建议
  硬伤: 无数据支撑的信号、单一因子信号
```

## 模板3: 数据分析任务（中风险）

```
触发: 手动 "分析xxx"
条件: 数据已就绪

链: Researcher → Analyst → (可选 Reviewer)

Researcher: 采集+清洗数据
Analyst: 分析+可视化
Reviewer: 仅在结果需要外发时启用
```

## 模板4: 代码开发（中风险）

```
触发: 手动 "写xxx" / "改xxx"
条件: 明确需求

链: Developer → (可选 Reviewer)

Developer (glm-5.1, terminal+file+execute_code):
  遵循 Superpowers 7步工作流
  产出: 代码 + 测试

Reviewer: 仅在涉及生产环境/数据管线核心脚本时启用
```

## 模板5: 日常维护（低风险—单agent）

```
触发: cron / 手动
不启用 Role 链

直接 domain agent 处理:
  - bug修复 → code-domain
  - 配置调整 → ops-domain
  - 选品上架 → ec-domain
```

## 模板选择决策树

```
任务
├─ 外发内容(公众号/消息推送)？ → 模板1 (全链)
├─ 交易信号/投资建议？       → 模板2 (R→A→R)
├─ 数据分析报告(外发)？       → 模板3 (R→A→R)
├─ 数据分析(内部)？           → 模板3 (R→A)
├─ 生产代码？                → 模板4 (D→R)
├─ 开发代码？                → 模板4 (D only)
└─ 日常维护？                → 模板5 (单agent)
```
