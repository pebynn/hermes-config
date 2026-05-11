# System Architecture — 2026-05-10

## 层架构

```
┌─── 协调层(Role横向) ───┐   ┌── 能力层(Domain纵向) ──┐
│ Researcher→Creator→     │   │ code │ ops │ research   │
│ Reviewer→Synthesizer    │   │ finance │ writing │ ec │
├─── 质量层(Gate纵向) ────┤   ├── 智能层(Reasoning) ───┤
│ data_guard(字段验证)    │   │ graphify(65K节点/78MB)  │
│ Reviewer(语义审查)      │   │ sequential-thinking     │
│ quality_score(量化评分) │   │ deep-research(9角度)    │
├─── 记忆层 ──────────────┤   │ brainstorming(设计)     │
│ MEMORY(5铁律)           │   └─────────────────────────┘
│ lessons/(7域150+条)     │
│ graphify知识图谱        │
└─────────────────────────┘
```

## 知识串联 (2026-05-10)

```
新教训 → lesson_inject.py → global.md
    ↓ (自动触发)
lesson_graph_bridge.py → graphify节点
    ↓
cross-domain-sync(cron) → 跨域关联边
    ↓
分析任务 → graph_search → enforce_delegate.py → 注入context
```

## 强制执行层

| 脚本 | Cron | 强制执行 |
|:--|:--|:--|
| enforce_delegate.py | pre-delegate | lesson_inject + 死路 + 5铁律 |
| cost-circuit-breaker.py | hourly | 日>$3.00暂停高消费cron |
| rule_audit.py | 10:00 daily | 违规用语扫描 |
| auto_review.py v2 | 09:00 daily | 系统健康+配置+教训+成本 |
| data_guard.py | 06:00 daily | 数据铁律门禁 |

## 规则来源层级

```
MCP硬约束 > 脚本强制 > SOUL.md核心规则 > profiles/域规则 > lessons/教训 > memory/偏好
```
