# D001: Kanban 架构替代 delegate_task 作为主调度机制

**日期**: 2026-05-11
**级别**: 🔴 架构级决策
**决策者**: 用户要求 → Hermes 执行

## 决策

将任务调度从 `delegate_task` 架构全面迁移到 **kanban** 架构：
- 所有 LLM 任务走 `kanban_create` → gateway dispatcher → worker
- 禁止直接使用 `delegate_task`
- 依赖链通过 `parents` 参数自动 promote

## 理由

1. **生命周期独立**: delegate_task 随父会话取消而终止；kanban 任务由 dispatcher 管理，独立生命周期
2. **可观测性**: kanban.db 提供任务状态持久化；delegate 无持久化
3. **依赖管理**: kanban 原生支持依赖图；delegate 需手动嵌套
4. **熔断保护**: kanban dispatcher 可配置连续失败熔断；delegate 无此机制
5. **委托深度限制**: delegate 硬限制 max_spawn_depth=3；kanban 支持扁平展开

## 代价

- 增加 kanban.db 维护成本
- 任务创建需走 B+D 注入流程（`bd_layer_enforce.py`）
- Worker 需遵守 kanban 完成协议

## 后续

- 2026-05-11: SOUL.md 写入 kanban 路由协议和 assignee 映射铁律
- 2026-05-11: B+D 注入层上线 (`bd_layer_enforce.py`)
- 2026-05-12: 发现 protocol_violation 新失败模式 → P001
- 2026-05-12: delegate 深度超限 → 全局教训 global.md
