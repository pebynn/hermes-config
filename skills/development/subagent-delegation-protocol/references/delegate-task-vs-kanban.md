# delegate_task vs Kanban — 决策指南 + 迁移手册

2026-05-11 完整审计结论

## 何时用 delegate_task

- 单次任务、5分钟内完成
- 不需要跨会话持久化
- 无多阶段依赖图
- 无硬阻断门禁需求
- 总指挥需要实时控制

## 何时升级到 Kanban

- 多阶段串行依赖（如电商三阶段 sourcing→listing→fulfillment、Role Chain）
- 跨天持久化要求
- Reviewer 硬阻断门禁
- 永久审计轨迹
- 任务需要跨总会话崩溃存续

## 互调规则（硬约束）

```
✅ kanban worker → delegate_task     (worker内部并行执行)
❌ delegate_task子代理 → kanban_create (无限嵌套风险)
❌ 总指挥 → delegate_task            (kanban模式下总指挥只用kanban工具)
```

## 总指挥工具集变化

```
移除: delegate_task
新增: kanban_create, kanban_show, kanban_comment, kanban_block
保留: memory, hindsight_*, read_file, write_file, patch, search_files,
      web_search, web_extract, terminal, cronjob, skill_*, todo
```

## 迁移：电商三阶段

```
旧 (delegate_task):
  总指挥 → delegate_task(ec-domain, "sourcing选品") → 等结果
         → delegate_task(ec-domain, "listing上架") → 等结果
         → delegate_task(ec-domain, "fulfillment履约")

新 (kanban):
  总指挥 → kanban_create(T1: sourcing, assignee=ec-sourcing)
         → kanban_create(T2: listing, assignee=ec-listing, parents=[T1])
         → kanban_create(T3: fulfillment, assignee=ec-fulfillment, parents=[T2])
  # 一次性创建完，dispatcher自动处理依赖推进
```

## 迁移：内容发布 Role Chain

```
旧:
  cron → delegate_task(writing-domain) 全包（采集+写作+审查+发布）
  Reviewer靠文本rule提醒，经常被跳过

新:
  kanban_create(T1: researcher, research-domain, parents=[])
  kanban_create(T2: writer, writing-domain, parents=[T1])
  kanban_create(T3: reviewer, reviewer, parents=[T2])  ← FAIL→block自动阻断
  kanban_create(T4: publisher, ops-domain, parents=[T3])
```

## Role Chain 脚本废弃清单

kanban 原生替代以下三个脚本：

| 旧脚本 | kanban替代 | 
|:--|:--|
| role_chain.py | parents依赖图 + reviewer worker独立profile |
| quality_score.py | reviewer worker的kanban_complete metadata |
| pipeline_checkpoint.py | kanban SQLite持久化 |

## 域/角色映射

delegate_task的6个能力域 → kanban的9个角色worker：

| delegate_task域 | kanban worker | 模型 | workspace |
|:--|:--|:--|:--|
| ec-domain | ec-sourcing + ec-listing + ec-fulfillment | pro/flash/flash | ~/PDD |
| writing-domain | writer + reviewer | pro/pro | ~/writing-data / scratch |
| finance-domain | finance | pro | ~/quant |
| code-domain | code | glm-5.1 | scratch |
| ops-domain | ops | flash | scratch |
| research-domain | research | pro | scratch |

## 在 kanban 架构中保留不变

- data_guard.py：数据质量门禁
- auto_review.py v2：跨域系统审计
- rule_audit.py / drift_detect.py：合规扫描
- cost-tracker / cost-circuit-breaker：成本管控
- lesson_inject.py / notify.py
- 30+ no_agent script cron

## 成本对比

| 维度 | delegate_task | Kanban |
|:--|:--|:--|
| 单任务开销 | 0（会话内） | +5K tokens worker启动 |
| 失败恢复 | 手工重试 | dispatcher自动retry |
| 多阶段 | 手工串行编排 | 自动依赖图 |
| 跨会话 | 不可能（会话绑定） | 原生SQLite持久化 |
| 审计轨迹 | session日志 | 永久任务事件日志 |
