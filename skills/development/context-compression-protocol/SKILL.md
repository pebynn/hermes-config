---
allowed-tools:
- delegate_task
- read_file
- memory
- session_search
author: unknown
description: 上下文压缩协议 — 智能管理长期会话中的上下文窗口，避免信息膨胀和过期数据污染
execution: auto
name: context-compression-protocol
trigger:
- 当前会话超过30次工具调用时
- 子代理返回结果超过5KB时
- 用户连续下达3个以上指令时
version: 1.4.0
---

# 上下文压缩协议

## 背景

借鉴 Claude Code 的 compact 系统:
- `/compact` 命令用 forked agent 总结对话历史，插入边界消息
- MicroCompact: 基于时间的过期工具结果自动清除（FileRead/Bash/Grep 等只读工具结果）
- 压缩保留：用户意图、文件路径、代码修改、pending tasks
- 压缩丢弃：过时的 shell 输出、旧的文件读取结果、已完成的任务详情

Hermes 的挑战：作为总指挥，我的上下文包含大量 delegate_task 的子代理结果。这些结果在任务完成后就是过时数据，不应继续占用上下文。

## 触发规则

| 条件 | 行为 |
|:----|:----|
| 工具调用 > 30 次 | 自动启动压缩 |
| 子代理返回结果 > 5KB | 摘要化（只保留结论，丢弃中间过程） |
| 同一任务链 3 个以上 delegate | 只保留最后一个的结果摘要 |
| 上次结果后已过 10 轮对话 | 旧的结果标记为过期，纳入压缩 |

## ⚠️ 关键陷阱：内置压缩引擎会破坏 tool_calls 格式

Hermes 内置的 `compression` 引擎（`~/.hermes/config.yaml` 中的 `compression.enabled: true` / `context.engine: compressor`）存在已知缺陷：它删除 tool 返回消息（role=tool）但不删除对应的 assistant tool_calls 消息。

导致 DeepSeek API 报错：
```
400 - "An assistant message with 'tool_calls' must be followed by tool messages responding to each 'tool_call_id'"
```

**这表明本技能描述的"手动压缩协议"和 Hermes 内置的自动压缩引擎是两套机制，且内置引擎有 bug。本技能是对协议的设计蓝图；内置引擎不能可靠执行此协议。**

### 修复方案（2026-04-30 已应用）

```
compression:
  enabled: false         # 关闭内置压缩 — 宁可放大 context 也不要 API 400
  threshold: 0.5         # 保留，如重新启用可作为触发阈值
  target_ratio: 0.2      # 保留
  protect_last_n: 50     # 如重新启用，保护最近 50 轮消息不压缩
```

### ⚠️ 复发陷阱（2026-05-14 确认）

04-30修复后compression曾被重新启用(enabled: true, threshold: 0.7)，导致用户在极低上下文使用率(<15%)时触发压缩。这是已知bug的复发——内置引擎在远低于threshold时也触发压缩。

**必须的验证命令**（每次系统自检时执行）：
```bash
grep -A2 '^compression:' ~/.hermes/config.yaml | grep enabled
# 必须输出: enabled: false
```

如果发现enabled: true，立即改回false。**这个bug被多次修复又被多次意外回滚。考虑在BD层或rule_audit.py中增加compression状态检查，防止再次复发。**

### 替代的手动压缩（本技能推荐方案）

不要依赖内置引擎。改用以下手动方式控制上下文：
1. 定期调用 `session_search` 归档，用 `memory` 保存关键结论
2. 不再需要的中间结果在调度层面丢弃，只传摘要给下游 delegate
3. 出现 `tool_calls 孤儿` 错误时，立即 `/new` 重建会话

详细诊断记录见 `references/compression-toolcall-orphan-bug.md`。

## 压缩策略

### 策略 A: 结果摘要化

```python
# 压缩前（浪费）
result = delegate_task(goal="选品8件", ...)
# result 包含：采集过程详情、17网搜索过程、每个商品的下载日志、图片处理日志

# 压缩后（精炼）
# 结果摘要：
# - status: success
# - products: 7件
# - output: ~/PDD/商品/2026-04-28/listing-ready/
# - recommended: 卡彤网批冰丝衬衫(¥69.9)
# - full_log: ... (已归档，需要时可调 read_file)
```

### 策略 B: 分层记忆

```
短期记忆（当前会话）:
  - 用户的最新指令
  - 刚才子代理返回的结论摘要
  - pending tasks

中期记忆（同一天）:
  - 已完成任务的 key results
  - session_search 可追溯

长期记忆（跨天）:
  - memory 工具保存的精炼事实
  - skills 记录的工作流
```

### 策略 C: 时间衰减

- 超过 30 分钟的子代理结果 → 标记为 `[STALE]`，不再传递到后续 delegate
- 需要重新查阅 → 重新 delegate 或 read_file 读输出文件
- 这是超越 Claude Code 的地方：Claude Code 的 MicroCompact 只是清理 UI 展示，我能在调度层面主动控制context质量

## 执行流程

```
检测到触发条件
    ↓
1. 识别可压缩项：
   - 已完成 delegate 的结果
   - 超过 30 分钟的工具输出
   - 超过 5KB 的返回内容
    ↓
2. 生成摘要：
   - x 个子代理任务 → x 行摘要
   - 保留：结果状态、输出路径、关键数字
   - 丢弃：详细日志、中间过程
    ↓
3. 写入内存以备追溯
    ↓
4. 在后续 delegate 的 context 中使用摘要版本
```

## 示例

### 压缩前的一段 context 传给子代理

```
[开始] ec-domain sourcing 完成: 采集了8个跨平台热词(淘宝suggest:妈妈夏装2026新款...)
→ 搜索了17网
→ 打开商品详情页A(小凡网批-2409, ¥19)
→ 提取price:19, title:小凡网批高品质冰丝短袖...
→ 下载ZIP成功
→ 打开商品详情页B(恒旺网批-C836, ¥29)
→ ...全部7个商品的详细日志...
→ 最终输出 listing-ready/
```

### 压缩后

```
[ec-domain sourcing 摘要] 7件商品已下载到 ~/PDD/商品/2026-04-28/listing-ready/
推荐款: 卡彤网批冰丝衬衫(¥69.9), 恒旺网批国风T恤(¥49.9)
价格区间: ¥9-¥39
```

### 效果

- 上下文占用: **~80% 缩减**
- 关键信息: **100% 保留**
- 后续 delegate: **更快、更便宜、更准**

## 策略 E: Memory 物理压缩技术（v1.2 新增）

> 2026-05-10 实战验证：31条/5,962 chars → 13条/2,586 chars (-56%)

### 四步压缩法

```
1. 分类分级
   逐条标注：🔴CRITICAL(API映射/死路/fallback) | 🟠HIGH(cron/pipeline/domain) | 🟡MEDIUM(历史细节)
   
2. 去重检查
   对比 memory ↔ global.md ↔ domain-lessons
   已在 lessons 中有完整版本的 → 从 memory 删除
   示例: Sina API映射(global.md已完整) → memory只保留"数据来自API原始值"铁律
   
3. 合并同类
   同主题多条 → 合并为一条
   示例: 5条公众号相关(SEO/排版/发布/草稿箱/配图) → 1条"writing-domain全貌"
   
4. 下沉细节
   详细技术信息 → lessons/域文件
   速查索引 → memory
   示例: browser_publish.py完整流程 → writing-domain.md; memory只保留"Cookie每周刷新"
```

### 保留判断

| 保留在 memory | 迁移到 lessons |
|:--|:--|
| 每轮必查的铁律（数据准确性/API字段映射） | 详细实现步骤（browser_publish 14步流程） |
| 当前系统状态（模型路由/活跃cron/基建） | 历史教训上下文（为什么某方案被否决） |
| 死路标记（PDD API不可用） | 域级技术文档（data_guard架构设计） |
| 用户偏好（沟通风格/cost敏感） | 一次性修复记录（某次bug修复过程） |

### 效果验证

```bash
# 压缩后检查关键项是否保留
for kw in "API铁律" "死路" "DeepSeek" "智谱" "pipeline" "PDD" "QQ Bot"; do
  echo -n "$kw: "; grep -c "$kw" ~/.hermes/memories/MEMORY.md
done
# 每个关键词应 ≥1 且 ≤2（去重后）
```

> ⚠️ **这是最常见的盲区**：讨论上下文压缩时通常只关注对话历史，但系统提示词本身通常比对话历史更大。

### 诊断数据（最新：2026-05-10 执行后）

| 组件 | Token 估算 | 占比 | 变化 |
|:-----|:----------|:-----|:-----|
| SOUL.md | ~2,058 | 18% | 启动协议已瘦身(5步→3步, 跳过pipelines.json) |
| MEMORY (13条目) | ~647 | 6% | ✅ 5,962→2,586 chars (-56%), 31→13条 |
| USER PROFILE | ~445 | 4% | ✅ 3,874→1,780 chars (-54%), 29→8条 |
| Skills列表 (144个) | ~20,000 | 60% | ✅ 171→144, 18个无用技能已归档 |
| MCP工具定义 (233个) | ~3,750 | 11% | — |
| **合计** | **~26,900** | **100%** | 启动协议读取 ~5KB (原 ~35KB) |

每轮对话固定开销从 ~130KB → ~85KB (-35%)。

### 修复优先级（更新）

1. ✅ **Memory压缩**（2026-05-10）：5,962→2,586 chars (-56%)。方法见 策略E。
2. ✅ **USER压缩**（2026-05-10）：3,874→1,780 chars (-54%)。18条冗余合并为8条。
3. ✅ **删无用技能**（2026-05-10）：18个技能归档(游戏/音乐/视频/ML训练/智能家居等)，144保留。
4. ✅ **启动协议瘦身**（2026-05-10）：SOUL.md 读5文件→读3文件，跳过 pipelines.json(15KB)。
5. ✅ **Pipeline清理**（2026-05-10）：3条completed→归档，12→7条活跃。
6. **分层注入**：核心铁律每轮注入，域知识按需加载，历史细节 session_search → 见 策略F（框架已就绪，待域激活触发逻辑实现）。

### ⚠️ 批量操作陷阱（2026-05-10 教训）

执行 `mv` 批量归档技能时，脚本未做范围校验，将 18 个目标外的 89 个技能也移入归档。
必须在 2 分钟内检测并回滚。

**批量文件操作铁律**：
```bash
# ❌ 直接执行批量 mv/rm
for d in $LIST; do mv "$d" .archived/; done

# ✅ 三步法
# 1. 先 dry-run 列出所有将被操作的目标
for d in $LIST; do [ -d "$d" ] && echo "WILL MOVE: $d"; done | wc -l
# 2. 人工确认数量匹配预期
# 3. 执行，执行后立即验证
for d in $LIST; do [ -d "$d" ] && mv "$d" .archived/; done
echo "Moved: $(find .archived -name SKILL.md | wc -l), Expected: N"
```

此规则适用于所有批量 `mv`/`rm`/`cp` 操作，不限于技能管理。

### 检测方法

目标：系统提示词 < 15,000 tokens（当前~30K，砍半）。

```bash
python3 -c "
import os
total = sum(len(open(os.path.expanduser(f)).read()) for f in [
    '~/.hermes/SOUL.md', '~/.hermes/memories/MEMORY.md', '~/.hermes/memories/USER.md'
])
print(f'SOUL+MEMORY+USER: {total} chars ≈ {total//4} tokens')
print(f'+ skills(92KB) + MCP(~15KB) + core → ~{total//4 + 23000 + 3750} tokens')
"
```

| 维度 | Claude Code compact | Hermes 上下文压缩 |
|:----|:-------------------|:-----------------|
| 触发方式 | 用户输入 /compact 或自动 | 自动触发(30次调用/5KB/10轮) |
| 压缩对象 | 对话历史 | 子代理返回结果 + 旧工具输出 |
| 精度 | LLM 生成的摘要(可能丢细节) | 结构化摘要 + 文件级追溯 |
| 恢复机制 | 只能 /resume 恢复会话 | read_file 可读任意输出文件 |
| 超越点 | 需要用户主动或等自动触发 | 主动在下一个 delegate 前预清理 |

## 策略 F: 分层注入架构（v1.3 新增）

> 提案阶段，待 SOUL.md 启动协议修改后生效

### 问题

当前所有 memory + lessons 全量注入每轮对话，导致：
- 核心铁律被噪音稀释
- 域知识在无关域的任务中浪费 context
- 启动协议额外读取 pipelines.json(15KB) 即使所有 pipeline 在 WAIT

### 架构

```
┌─────────────────────────────────────────┐
│ Tier 1: 必注核心 (~2,000 chars)         │
│ → 5条用户铁律 + API映射速查 + 死路      │
│ → 每轮对话无条件注入                     │
├─────────────────────────────────────────┤
│ Tier 2: 域激活注入 (~2,000 chars)       │
│ → 按当前活跃域动态加载                   │
│ → writing活跃→注入公众号/SEO规则         │
│ → finance活跃→注入量化/信号规则          │
├─────────────────────────────────────────┤
│ Tier 3: 搜索调用 (按需)                 │
│ → session_search + lessons 全文          │
│ → 不在启动时注入，只在需要时检索         │
└─────────────────────────────────────────┘
```

### 启动协议对比

| | 现行 | 优化后 |
|:--|:--|:--|
| 读取文件 | daily.md + global.md + task_tracker + pipelines.json + self-diagnosis | daily.md(摘要) + global.md(死路+铁律段) + self-diagnosis |
| 注入量 | ~35KB | ~5KB |
| pipelines | 每次注入 15.7KB | 仅在状态变化时读取 |

### 实现

修改 SOUL.md 启动协议：
1. `read_file daily.md offset=0 limit=20` → 只读待办段
2. `read_file global.md` → 只读 🗑️死路 + 🔴CRITICAL 段
3. `task_tracker.json` → 只统计 P1 数量
4. 跳过 `pipelines.json`，有变化才读
5. self-diagnosis 不变
