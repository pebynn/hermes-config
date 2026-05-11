---
allowed-tools:
- delegate_task
- terminal
- file
author: unknown
description: 批量代理处理 — 数据并行模式，每个数据项 spawn 一个子代理并发处理
execution: auto
name: batch-agent-processing
trigger:
- 需要批量处理多个独立数据项时（商品、股票、文件）
- 每个数据项的处理互不依赖时
- 任务可拆分为 N 个独立子任务时
version: 1.0.0
---

# 批量代理处理（Batch Agent Processing）

## 背景

借鉴 OpenAI Codex CLI 的 `spawn_agents_on_csv` 模式：
- 每行 CSV spawn 一个 worker 子代理
- 支持 max_concurrency（默认16）
- 每个 worker 有独立超时（默认1800s）
- Worker 通过 `report_agent_job_result` 回传结果
- 自动收集到输出 CSV

## Hermes 实现

在 Hermes 中，通过 `delegate_task(tasks=[...])` 实现相同的效果：

```python
# 基础用法：每个商品 spawn 一个子代理
results = delegate_task(tasks=[
    {"goal": "处理商品A: 下载→去水印→生成listing", "toolsets": ["terminal","file"]},
    {"goal": "处理商品B: 下载→去水印→生成listing", "toolsets": ["terminal","file"]},
    {"goal": "处理商品C: 下载→去水印→生成listing", "toolsets": ["terminal","file"]},
])
```

## 触发条件

以下任一情况自动使用 batch 模式：

1. **多个商品需要处理**（>2件）→ 每件 spawn 一个子代理
2. **批量 A 股分析**（>5只股票）→ 每只股票 spawn 一个子代理
3. **多文件并行操作**（>3个文件）→ 每个文件 spawn 一个子代理
4. **跨平台数据采集** → 淘宝/拼多多/抖音各一个子代理

## 适用场景

### 电商场景

```python
# — 场景1：多商品并行下载 —
# 不用：依次下载商品A、商品B、商品C（串行，慢）
# 要用：
results = delegate_task(tasks=[
    {"goal": "从17网下载商品A并去水印", "context": "商品ID: 2409, 品类: 连衣裙", "toolsets": [...]},
    {"goal": "从17网下载商品B并去水印", "context": "商品ID: 2410, 品类: T恤",   "toolsets": [...]},
    {"goal": "从17网下载商品C并去水印", "context": "商品ID: 2411, 品类: 套装",  "toolsets": [...]},
])

# — 场景2：多商品上架准备并行 —
results = delegate_task(tasks=[
    {"goal": "为商品A生成AI标题+定价+SKU", "context": f"listing: {dir_A}"},
    {"goal": "为商品B生成AI标题+定价+SKU", "context": f"listing: {dir_B}"},
    {"goal": "为商品C生成AI标题+定价+SKU", "context": f"listing: {dir_C}"},
])
```

### A 股场景

```python
# 并行分析多只股票
results = delegate_task(tasks=[
    {"goal": "分析000001: PE/ROE/技术指标", "context": "代码: 000001"},
    {"goal": "分析000002: PE/ROE/技术指标", "context": "代码: 000002"},
    {"goal": "分析000003: PE/ROE/技术指标", "context": "代码: 000003"},
])
```

### 采集场景

```python
# 跨平台并行采集
results = delegate_task(tasks=[
    {"goal": "采集淘宝中老年女装热词", "toolsets": ["web"]},
    {"goal": "采集拼多多中老年女装热词", "toolsets": ["web"]},
    {"goal": "采集抖音中老年女装趋势", "toolsets": ["web"]},
])
```

## 超时与容错

| 参数 | 默认值 | 说明 |
|:----|:------|:----|
| 单子代理超时 | 180s | 足够完成下载或选股 |
| 最大并发 | 3 | Hermes delegate_task 默认限制 |
| 失败处理 | 单个失败不中断整体 | 结果中标记 failed |
| 超时处理 | 超时自动跳过 | 返回 TIMEOUT 状态 |

## 与 Codex spawn_agents_on_csv 对比

| 特性 | Codex spawn_agents_on_csv | Hermes delegate_task batch |
|:----|:-------------------------|:--------------------------|
| 输入 | CSV文件 + 指令模板 | tasks 数组（每个独立 goal） |
| 输出 | 结果 CSV 自动导出 | 返回结果数组 |
| 子代理通信 | report_agent_job_result 回传 | 通过 context 字段传参 |
| 并行度 | 默认16，可配置 | 默认3，可配置 |
| 超时 | 1800s per worker | 最长600s（可 background） |
| 隔离 | 每个 worker 独立会话 | 每个 task 独立子代理 |
| 模板 | 指令模板 + {column} 占位符 | 每个 goal 自定义 |

## 关键规则

1. **数据项必须互不依赖** — 不能有跨任务的共享状态或顺序要求
2. **每个 goal 自包含** — 子代理不知道其他子代理的存在
3. **使用结构化结果** — 每个子代理返回一致的结果格式（status, output, error 等）
4. **不要分太细** — 单个子代理至少能独立完成一个完整步骤
