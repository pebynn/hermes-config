# P001: Kanban Protocol Violation — Worker 完成但不通知调度器

**出现次数**: 3+ (strat-c ×2, strat-a ×1)
**跨域**: ops-domain, finance-domain
**首次发现**: 2026-05-12
**严重度**: 🟠 HIGH

## 特征

1. Worker 正常运行 30-40 分钟（心跳持续发送）
2. 进程退出码 `rc=0`（正常完成）
3. **未调用 `kanban_complete` 通知调度器**
4. 触发 `protocol_violation` 事件
5. 重试耗尽 → `gave_up`

## 与其它失败模式的区别

| 模式 | rc | 心跳 | 完成通知 | 根因 |
|:--|:--|:--|:--|:--|
| pid not alive | - | 停止 | N/A | Worker 崩溃 |
| exited code 1 | 1 | 持续 | N/A | Worker 错误退出 |
| **protocol_violation** | **0** | **持续** | **缺失** | Agent 未感知退出 |

## 实例

### strat-c (缠论趋势进化)
- 第 2 次运行: 2026-05-12, 32min, rc=0 → protocol_violation
- 第 3 次运行: 2026-05-12, 41min, rc=0 → protocol_violation
- 最终: `gave_up`

### strat-a (动量策略)
- t_68f3487c: 2026-05-13, rc=0 → protocol_violation → blocked

## 根因

LLM agent 在 worker 进程退出时未触发 completion hook：
- Agent session 可能在 worker 运行期间已结束
- Worker 进程退出信号未被 agent 感知
- 导致 `kanban_complete` 从未被调用

## 修复

1. **Worker wrapper 加 atexit/signal handler**: 进程退出时自动调用 kanban API 上报状态
2. **Dispatcher 侧防御**: 检测到 worker 进程退出但无 completion 通知 → 主动查询 worker 状态
3. **超时兜底**: 设置 `max_runtime_seconds`，超时自动标记 completed

## 关联

- [D001: Kanban 架构迁移](../decisions/2026-05-11-kanban-migration.md) — 此模式是 kanban 架构的原生风险
- [ops-domain.md](~/.hermes/lessons/ops-domain.md) — "Kanban Worker 完成协议违规"
- Session: `cron_ef7f14899ef1_20260513_032537`
