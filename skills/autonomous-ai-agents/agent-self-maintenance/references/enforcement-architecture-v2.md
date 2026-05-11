# Enforcement Architecture v2 (2026-05-10)

## Problem
纯文本约束(SOL.md段落/独立lesson)对LLM agent约束力为零。多次被用户指出"文本约束对你没用"。

## Four-Layer Design

```
L0: memory注入 (系统级, 100%强制)
    → 铁律短格式每回合自动注入
    → 分析类任务必须 graph_search→sequential-thinking
    → 代理无法跳过

L1: enforce_delegate v2 (唯一入口)
    → lesson_inject + dead_list + graph_search(分析类自动触发)
    → 死路命中→BLOCKED退出

L2: rule_audit v2 (cron 10:00)
    → 扫描session文件, CRITICAL违规→自动暂停cron

L3: cost-circuit-breaker (cron hourly)
    → 日成本>$3.00→暂停高消费cron
```

## Design Principle
能脚本化的不靠文本，能cron审计的不靠自觉，能MCP硬约束的不靠prompt。
