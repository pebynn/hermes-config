# Supervised Pipeline Pattern — Text Checklist ≠ Execution

> Triggered by: P1/P2 进化任务清单在external-evolution-ecosystem.md躺了N天，零跟进。
> Core lesson: 任何跨任务清单必须同时部署执行机制+监督机制，纯文档清单是不可靠的。

## Problem

用户在跨 session 的对话中下了"评估外部进化生态、读论文、补护栏"的指令后，Orchestrator 产出了一个分析文档（external-evolution-ecosystem.md），底部列了 7 条 Action Items。文档声称 `[x]` 了 3 条 P0，P1/P2 各 4 条。

实际上：
- P0 3条确实在当时 session 做完了
- P1 4条只存在于文档的 checkbox 里，无 kanban 任务、无 cron、无跟进机制
- 用户发现后质问："这些东西都得我来一个个提醒你吗"

## Root Cause

Action Items 清单是 **纯文本**。没有执行载体，没有超时检测，没有阻塞报告。唯一的"监督"是用户自己记得去查。

这是 agent-self-maintenance skill Pitfall 16/17/23 的具体案例：Multi-phase plans without execution mechanism are not credible。

## Solution: 3-Step Fix

### Step 1: 所有待办 → kanban 任务

```bash
# P1 依赖链
hermes kanban create "SkillClaw论文分析 vs B+D层对比" --assignee research-domain --body "..."
hermes kanban create "EvoClaw退化检测cron实现" --assignee code-domain --parent <t1_id> --body "..."
hermes kanban create "综合进化升级方案" --assignee research-domain --parent <t2_id> --body "..."

# P2 并行（无依赖）
hermes kanban create "Tool描述优化调研" --assignee research-domain --body "..."
hermes kanban create "System Prompt优化调研" --assignee research-domain --body "..."
hermes kanban create "遗传算法轻量借鉴研究" --assignee research-domain --body "..."
hermes kanban create "awesome-hermes-agent季度监控cron" --assignee code-domain --body "..."
```

关键：P1 用 `--parent` 建立线性依赖，子任务自动在父任务 `done` 后 promote 到 `ready`。

### Step 2: 部署监督 cron

创建一个 no_agent cron 脚本 `evolution_pipeline_supervisor.py`：

```python
#!/usr/bin/env python3
"""每周检查 P1/P2 任务状态。阻塞/失败→QQ Bot告警。正常→静默。"""
```

脚本逻辑：
- 对所有 tracked task IDs 执行 `hermes kanban show --json`
- 任何 `failed` → P0 告警
- 任何 `blocked` → P1 告警
- 父任务 `done` 但子任务仍 `todo`（dispatcher 未 promote）→ P1 告警
- 同一任务连续两周 `todo` → P2 停滞告警
- 全部 `done` → P3 完成通知
- 一切正常 → 静默输出（零 token 递送）

注册 cron：`hermes cronjob create --name "进化管线监督器" --schedule "0 9 * * 1" --no_agent true --script evolution_pipeline_supervisor.py --deliver qqbot:...`

### Step 3: 更新跟踪文档

将文档中的纯文本 checklist 替换为 kanban 任务 ID + 状态表：

```markdown
### P1 — KANBAN TRACKED (dispatcher auto-pickup)
- [~] t_ae9ffb59 (research-domain, running): SkillClaw论文分析
- [ ] t_457f1d86 (code-domain, todo, parent=t_ae9ffb59): EvoClaw退化检测cron
- [ ] t_f7386342 (research-domain, todo, parent=t_457f1d86): 综合进化升级方案

### Supervision
- Cron `34b839a57e6f` (每周一 09:00): 自动检查P1/P2进度
```

## Verification

```bash
# 检查任务链
hermes kanban list | grep -E "t_ae9ffb59|t_457f1d86|t_f7386342|t_5eed626c|t_48bdb336|t_f6de2309|t_c197c415"

# 手动触发监督脚本（看看会不会静默/告警）
python3 ~/.hermes/scripts/evolution_pipeline_supervisor.py

# 检查 cron 注册
hermes cronjob list | grep 进化管线
```

## Why This Works

| 组件 | 作用 | 零用户干预 |
|:--|:--|:--|
| kanban 任务 | 执行载体，dispatcher 自动拾取 | ✅ |
| dependency chain | 串行依赖自动 promote | ✅ |
| supervision cron | 每周一自动查进度 | ✅ |
| QQ Bot 告警 | 阻塞/失败推送用户 | ✅ |
| 静默设计 | 正常推进零干扰 | ✅ |

## Anti-Patterns That Preceded This

1. **Action Items 清单放文档不建任务** → 无人跟踪，等用户提醒
2. **假设 dispatcher 会完美工作** → 没有监督 cron，依赖 promote 失败无人知晓
3. **单点报告（文档更新）替代持续监督** → 写完文档 ≠ 任务会自己完成

## Related

- agent-self-maintenance §Pitfall 16: Multi-phase plans without execution mechanism
- agent-self-maintenance §Pitfall 17: 架构思路必须落地为操作路径
- kanban-orchestrator §Multi-Round Evolution Loop: 回合间监督模式
- Script: `~/.hermes/scripts/evolution_pipeline_supervisor.py` (可复用模板)
