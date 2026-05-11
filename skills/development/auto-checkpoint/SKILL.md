---
name: auto-checkpoint
description: Auto-detect long sessions, extract summary checkpoint, prompt user to /new for token savings
version: 1.0.0
author: hermes
tags: [cost-optimization, session-management, checkpoint]
---

# Auto Checkpoint — Session 长度感知 + 自动摘要 + /new 提示

## 触发规则

会话中每次响应用户时，在回复末尾静默检查以下条件：

| 条件 | 动作 |
|:-----|:-----|
| 本轮数 > 50 | 生成 checkpoint 摘要 + 提醒 /new |
| 本轮数 > 80 | **强制**生成 checkpoint + 强烈建议 /new（不继续处理复杂任务） |
| 单次回复 > 5000 chars | 说明本轮已长，建议确认后 /new |
| 用户说"太长了/好慢/好贵" | 立即生成 checkpoint + 建议 /new |

## Checkpoint 摘要格式

写入 `~/.hermes/checkpoints/session_<YYYYMMDD_HHMMSS>.md`，内容：

```markdown
# Session Checkpoint — <日期 时间>

## 本次对话目标
<1-2句话>

## 已完成
- [x] 事项1
- [x] 事项2

## 关键结论/产物
- 文件路径、配置变更、决策记录

## 待继续
- [ ] 待办1
- [ ] 待办2

## 恢复指令
直接粘贴此文件内容到新会话，说"继续这些任务"
```

## 回复模板

生成 checkpoint 后在回复末尾追加：

```
---
📊 本轮对话已达 <N> 轮，已生成 checkpoint：
~/.hermes/checkpoints/session_<timestamp>.md

建议：/new → 粘贴此文件内容 → 继续。当前上下文越长，每轮开销越大。
```

## 强制模式（>80轮）

超过 80 轮后，拒绝处理新的复杂任务，回复：

```
⚠️ 本轮已达 <N> 轮，token 成本显著上升。
已生成 checkpoint：~/.hermes/checkpoints/session_<timestamp>.md
请 /new 后粘贴继续。在新会话中我会直接执行上述待办。
```

## 统计规则

- 当前轮数 = 对话中 user/assistant 往返次数（不是消息数）
- 首次加载此 skill 时轮数算 1，后续每轮 +1
- 跨 session 不累积统计

## 与非 checkpoint 的协作

- 如果用户正在执行复杂任务（如量化回测），等当前子任务完成再提醒
- 如果用户说"等一下/先做完这个"，跳过本轮提醒
- 已生成的 checkpoint 不需要重复生成，更新文件内容即可

## 与 Task Checkpoint (P4) 的区别

本 skill 负责 **会话层面** 的 checkpoint — 检测对话轮数过多时生成摘要，建议用户 /new 以节省 token。产出的是人类可读的 Markdown 摘要，供用户粘贴到新会话。

`agent-self-maintenance` 中的 P4 Task Checkpoint 负责 **任务执行层面** 的 checkpoint — 保存长跨度任务的执行状态（当前阶段、产物、决策、下一步），供主代理自动恢复。产出的是 JSON 机器可读状态文件。

两者可以共存：
- 50轮时 auto-checkpoint 提示 "保存摘要，建 /new"
- 同时 checkpoint.json 已记录 "任务在阶段3，继续验证隔离"
- 新会话启动 → 协议检测 checkpoint.json → 自动恢复 → 不会丢失进度

本 skill 不负责检查或恢复 task checkpoint。那是 `using-superpowers` 启动协议的工作。
