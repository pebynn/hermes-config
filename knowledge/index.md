# Hermes 知识库索引

> 最后更新: 2026-05-14 03:30 CST
> 来源: 所有域 lessons + 会话审计 + 决策记录

## 📂 目录结构

| 目录 | 用途 | 条目数 |
|:--|:--|--:|
| [decisions/](decisions/) | 关键架构决策（含决策+理由+代价+后续） | 4 |
| [evolution/](evolution/) | 系统演化时间线（Phase+核心教训） | 1 |
| [patterns/](patterns/) | 重复出现的故障模式（特征+实例+根因+修复） | 4 |

## 🏗️ 架构决策

| ID | 日期 | 标题 | 级别 |
|:--|:--|:--|:--|
| D001 | 2026-05-11 | [Kanban 架构替代 delegate_task](decisions/2026-05-11-kanban-migration.md) | 🔴 |
| D002 | 2026-05-12 | [B+D 层脚本强制执行](decisions/2026-05-12-bd-layer-script-enforcement.md) | 🔴 |
| D003 | 2026-05-13 | [行业映射数据源危机](decisions/2026-05-13-industry-mapping-crisis.md) | 🟠 |
| D004 | 2026-05-13 | [策略B PEAD 宣告不可达](decisions/2026-05-13-pead-strategy-unreachable.md) | 🔴 |

## 🔁 重复故障模式

| ID | 模式 | 出现次数 | 跨域 |
|:--|:--|--:|:--|
| P001 | [Kanban Protocol Violation](patterns/kanban-protocol-violation.md) | 3+ | ops/finance |
| P002 | [量化回测 OOM](patterns/oom-finance-pipeline.md) | 1 | finance |
| P003 | [盲重试循环](patterns/blind-retry-cycles.md) | 2+ | finance/ops |
| P004 | [量化回测前瞻偏差](patterns/lookahead-bias-backtesting.md) | 2 | finance |

## 📈 系统演化

| ID | 标题 | 时间跨度 |
|:--|:--|:--|
| E001 | [Hermes Agent 架构演进](evolution/hermes-agent-architecture.md) | 2026-04 → 2026-05 |

## 🔗 关联资源

- Lessons 目录: `~/.hermes/lessons/` (8 域 + 5 日审计)
- Graphify 知识图谱: MCP graphify (204K+ 节点)
- SOUL.md: `~/.hermes/SOUL.md`
- Cron 调度: `cronjob action=list`
