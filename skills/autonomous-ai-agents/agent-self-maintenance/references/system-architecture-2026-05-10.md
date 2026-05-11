# Hermes Agent 系统架构 — 2026-05-10

## 总览

```
用户(CLI/QQBot)
    ↓
┌─────────────────────────────────────────────────┐
│  Hermes Gateway (PID 75270, 运行38h+)            │
│  消息路由 / session管理 / 多平台适配              │
└──────┬──────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│  主代理 (deepseek-v4-pro)                        │
│  SOUL.md(83行) — 调度决策核心                    │
│  ├─ 决策矩阵 L1/L2/L3                            │
│  ├─ 调度速查表(lesson_inject嵌每条路径)           │
│  └─ 6域资源表                                    │
└──────┬──────────────────────────────────────────┘
       ↓ delegate_task
┌──────────────────────────────────────────────────┐
│            6个域子代理 (Domain Agents)             │
├──────────┬──────────┬──────────┬─────────────────┤
│ code     │ ops      │ research │ finance         │
│ glm-5.1  │ v4-pro   │ v4-pro   │ v4-pro          │
│ 编码/git │ 运维/cron│ 深度调研 │ 量化/基本面      │
├──────────┴──────────┼──────────┴─────────────────┤
│ writing             │ ec (暂停)                   │
│ v4-pro              │ v4-pro                      │
│ A股内容自动化        │ 电商选品→上架→运营          │
└─────────────────────┴────────────────────────────┘
```

## 强制脚本层

| 脚本 | 触发 | 作用 |
|:--|:--|:--|
| enforce_delegate.py | 每次delegate前 | lesson_inject+死路检查+铁律注入 |
| cost-circuit-breaker.py | 每小时cron | 日消耗>$3.00自动暂停高消费cron |
| rule_audit.py | 每日10:00 cron | 扫描违规用语/死路提及 |
| data_guard.py | 每次发布前 | 字段验证+AI味检测+函数漂移 |
| auto_review.py v2 | 每日09:00 cron | 系统健康+配置一致性+教训扫描 |

## MCP 工具链 (15个Server)

| 类别 | Server | 用途 |
|:--|:--|:--|
| 治理 | skill-auditor, cost-guard, prompt-optimizer, security-auditor | 安全+成本+指令 |
| 知识 | graphify(65K节点), llm-wiki, sequential-thinking | 推理+知识 |
| 研究 | web-search, web-extract, deep-research | 信息采集 |
| 数据 | stock-sdk, mysql | A股行情+数据库 |
| 调度 | hermes-delegate, hermes-cron | 任务队列+定时 |
