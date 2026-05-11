# GitHub #344 多智能体架构 — 跟踪与落地

> Issue: https://github.com/NousResearch/hermes-agent/issues/344
> 目标: Hermes 从单智能体+隔离子代理 → 真正的多智能体系统

## 当前已落地（2026-05-10）

| #344 特性 | 实现方式 | 状态 |
|:--|:--|:--|
| Agent Roles | 6域代理(code/ec/ops/research/finance/writing)各有专用模型+工具集 | ✅ |
| Convoy Mode | `dispatching-parallel-agents` skill 实现并行分支→汇总 | ✅ |
| L1 Result Passing | 上游子代理输出作为下游context注入 | ✅ |
| Failure Recovery | 三级恢复(重试→重规划→分解)已写入SOUL.md规则5 | ✅ |
| Checkpointing | `pipeline_checkpoint.py` 保存/恢复阶段状态 | ✅ |

## 需要上游支持（跟踪中）

| #344 特性 | 依赖 | 跟踪方式 |
|:--|:--|:--|
| Workflow DAG Engine | delegate_task 核心改造 | GitHub issue 订阅 |
| L2 Shared Scratchpad | 共享KV存储基础设施 (#377) | 关联 issue |
| L3 Live Dialogue | 智能体间实时对话 (#376) | 关联 issue |
| Persistent Agent Roles | 角色持久化+自动分配 | Phase 3 跟踪 |
| Cross-Platform Agent | 跨机器分布式 | Phase 4 跟踪 |

## 跟踪策略

1. **每周一 cron** (`hermes-cron`): 检查 #344 和关联 issues 状态变化
2. **发现可用特性**: 立即评估→方案→用户确认→集成
3. **Phase 标记**: 
   - Phase 1-2 (进行中) → 每周检查
   - Phase 3-4 (规划中) → 每月检查

## 可自行增强的部分（不等上游）

1. **Agent Role 模板化**: 为常用任务模式预定义 agent role + toolsets 组合
2. **结果质量评分**: 子代理返回后自动评分，低于阈值触发 Reviewer 角色复核
3. **工作流模板库**: 将常见跨域任务（如"数据→分析→写作→发布"）固化为可复用模板
