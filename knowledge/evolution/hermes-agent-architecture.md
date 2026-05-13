# E001: Hermes Agent 架构演进时间线

**时间跨度**: 2026-04 → 2026-05
**最后更新**: 2026-05-14

## Phase 1: delegate_task 时代 (2026-04 中旬)

- 使用 `delegate_task` 作为唯一子代理调度机制
- 限制: max_spawn_depth=3，任务随父会话取消而终止
- 核心教训: 子代理长任务必须用 cron，禁止 delegate

## Phase 2: delegate + cron 混合 (2026-04 下旬 → 05 上旬)

- 长任务迁移到 cronjob
- skills 体系扩展 (50+ skills)
- MCP server 上线: stock-sdk, mysql, graphify, cost-guard
- 核心教训:
  - API Token 过期 → 全系统级联故障 (05-08)
  - 纯文本 SOUL.md 规则不可靠
  - Pip install 被禁止 → 用 uv tool install

## Phase 3: Kanban 架构 + B+D 注入 (2026-05-11 →)

### 05-11: Kanban 全面上线
- delegate_task → kanban_create 迁移
- B+D 层协议写入 SOUL.md
- 教训: 同日发现 2 次 L2 决策矩阵违规 → 纯文本约束不可靠

### 05-12: 脚本化强制执行
- `pre_kanban_create.py` / `post_kanban_complete.py` 上线
- `audit_bd_layer.py` 审计 cron 创建
- 新发现: protocol_violation 模式 (P001), delegate 深度超限

### 05-13: 策略管线震荡
- finance-domain: 行业映射覆盖危机 (D003) — SECTOR_HEAT覆盖率仅0.4%
- finance-domain: 策略B PEAD 宣告不可达 (D004) — 前瞻偏差致4轮迭代归零
- finance-domain: stop_loss 执行乐观偏差
- strat-a: protocol_violation 阻塞 (t_68f3487c)
- 新发现模式: 前瞻偏差 (P004)

## 核心教训

| # | 教训 | 阶段 |
|--:|:--|:--|
| 1 | 子代理长任务必须用 cron，禁止 delegate | Phase 1 |
| 2 | API Token 需自动检测+轮换+熔断 | Phase 2 |
| 3 | 纯文本约束不可靠 → 必须脚本化强制执行 | Phase 3 |
| 4 | Kanban worker 需 atexit hook 防止 protocol_violation | Phase 3 |
| 5 | 全量回测必须分批 + 内存预估 | Phase 3 |
| 6 | Worker 必须产出诊断信息，不能只返回 exit code | Phase 3 |
| 7 | 量化回测必须做前瞻偏差检测，净化前vs净化后差异>30% 🚨 | Phase 3 |

## 当前架构

```
┌─── Kanban 调度层 ─────────────┐
│ B注入 → kanban_create → D回收 │
│ dispatcher → dependency graph │
├─── Worker 层 ─────────────────┤
│ code │ ops │ research         │
│ finance │ writer │ reviewer   │
│ ec-sourcing/listing/fulfill   │
├─── 智能层 ────────────────────┤
│ graphify │ sequential-thinking │
│ deep-research │ brainstorming  │
├─── 强制执行层 ────────────────┤
│ bd_layer_enforce.py           │
│ cost-circuit-breaker.py       │
│ rule_audit.py │ data_guard.py │
└────────────────────────────────┘
```
