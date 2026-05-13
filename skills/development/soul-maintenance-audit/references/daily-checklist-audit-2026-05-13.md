# 每日清单体系审计 — 2026-05-13

## 发现的问题

| 文件 | 问题 | 严重度 | 修复 |
|:--|:--|:--|:--|
| pipeline.yaml | 7个cron ID不存在 (5896e6bcea04/d075c207d860/18619f5cdf16/704e9bfe5896/8dc31c90bf0d/60c82974423f/bc02d5952723) | 🔴 P0 | 映射到真实ID + 补6条新管线 |
| daily.md | cron数硬编码25→实际38 | 🔴 P0 | agenda_builder.py check_crons()重写 |
| task_tracker.json | 优先级P1→P2字段矛盾, resolved任务未移除 | 🟠 P1 | 对齐+清理 |
| fix-tasks.md | 8/8完成但未归档 | 🟠 P1 | → archive/ |
| nightly_summary.md | 引用退役Hindsight组件 | 🟠 P1 | 重写，移除Hindsight+更新状态 |
| state.json | 16B只有disk_pct | 🟡 P2 | 扩展至disk/memory/cron/graph/wiki |
| pending.md | 永远"暂无待办" | 🟡 P2 | 填入4条活跃任务 |

## agenda_builder.py 修复详情

1. **check_crons()**: 硬编码 `25, 25` → JSON解析 `hermes cron list --json`，动态计数 total/enabled
2. **get_today_pipelines()**: 死cron引用 → 真实管线 (05:35/11:35/17:40/23:35 热门事件 + 18:00 科普)
3. **check_data_freshness()**: 复盘文件名 `每日复盘` → `全天回顾`，cron ID d075c207d860 → 79e67133f2d0

## pipeline.yaml 真实cron映射

| 死ID | 功能 | 真实ID | 名称 |
|:--|:--|:--|:--|
| 5896e6bcea04 | collect_data | cb4e13762bf2 | 热门事件-隔夜速递(05:35) |
| d075c207d860 | generate_review | f54a3f9f759a | 热门事件-今日重磅(17:40) |
| 18619f5cdf16 | publish_xueqiu | 79e67133f2d0 | 热门事件-全天回顾(23:35) |
| 704e9bfe5896 | notify_completion | (已移除) | 热门事件管线自足 |
| 8dc31c90bf0d | morning_brief | e10e5bab3a4e | 热门事件-午间热榜(11:35) |
| 60c82974423f | lesson_promoter | 575103045eb1 + 6c2e69287dc7 | error-learner + BD-audit |
| bc02d5952723 | quant_weekly | (已移除) | 由信号引擎+周总结覆盖 |

## 新增管线

- knowledge_nightly: graphify(03:00) → lessons_sync(03:30) → knowledge_audit(03:35) → skill_sync(04:00) → wiki_sync(04:20)
- monitoring: kanban_block(每5m) + cron_watchdog(每30m)
- data_quality: data_guard_drift(06:00)
