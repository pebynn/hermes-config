# Hermes 全局数据总线 — v2

> 跨域数据契约标准化设计文档
> 版本: v2 | 2026-05-11

---

## 1. 概述

将原有的 pipeline-bus（仅覆盖 EC 选品→上架→运营三域）扩展为覆盖所有域的全域数据总线。

### 设计原则

1. **契约驱动** — 每个数据流有明确定义的 JSON Schema
2. **版本化** — 每个 schema 有独立版本号，支持向后兼容
3. **文件总线** — 生产者写入 `~/.hermes/bus/<stream_name>/` 目录，消费者通过 kanban context_from 或直接文件读取
4. **向后兼容** — 消费者必须能处理旧版本数据（v1→v2 字段只增不减）
5. **幂等写入** — 同一数据多次写入结果一致（覆盖式）

---

## 2. 数据流全景

| ID | 数据流 | 生产者 | 消费者 | Schema | 版本 |
|:---|:-------|:-------|:-------|:-------|:----|
| DS-01 | 量化信号→写作素材 | finance-domain | writer | `schema/quant-signal-to-writer.json` | v1 |
| DS-02 | 调研结果→知识图谱 | research-domain | graphify | `schema/research-to-graphify.json` | v1 |
| DS-03 | 审查反馈→写作改进 | reviewer | writer | `schema/reviewer-to-writer.json` | v1 |
| DS-04 | 故障诊断→代码修复 | ops-domain | code-domain | `schema/ops-to-code.json` | v1 |
| DS-05 | EC选品→上架 | ec-sourcing | ec-listing | `schema/ec-sourcing-to-listing.json` | v2 |
| DS-06 | EC运营→选品调整 | ec-fulfillment | ec-sourcing | `schema/ec-fulfillment-to-sourcing.json` | v1 |

---

## 3. 目录约定

```
~/.hermes/bus/
├── README.md                          ← 本文档
├── schema/                            ← JSON Schema 定义
│   ├── quant-signal-to-writer.json
│   ├── research-to-graphify.json
│   ├── reviewer-to-writer.json
│   ├── ops-to-code.json
│   ├── ec-sourcing-to-listing.json
│   └── ec-fulfillment-to-sourcing.json
├── quant-signal-to-writer/            ← DS-01 数据目录
│   └── {YYYY-MM-DD}.json
├── research-to-graphify/              ← DS-02 数据目录
│   └── {YYYY-MM-DD}-{topic}.json
├── reviewer-to-writer/                ← DS-03 数据目录
│   └── {YYYY-MM-DD}-{article}.json
├── ops-to-code/                       ← DS-04 数据目录
│   └── {incident_id}.json
├── ec-sourcing-to-listing/            ← DS-05 数据目录
│   └── {YYYY-MM-DD}-{goods_no}.json
└── ec-fulfillment-to-sourcing/        ← DS-06 数据目录
    └── {YYYY-MM-DD}-{period}.json
```

### 路径规范

- 每个数据流有自己的子目录（总线中的"车道"）
- 文件名：日期前缀 + 业务标识，确保自然排序和唯一性
- 写入策略：**覆盖式** — 同名文件直接覆盖，旧数据在 git 历史中可追溯

---

## 4. 公共元信息结构

所有数据流共享 `meta` 字段结构：

```json
{
  "meta": {
    "stream": "<stream_id>",
    "version": "v1",
    "producer": "<producer_domain>",
    "consumer": "<consumer_domain>",
    "produced_at": "2026-05-11T10:00:00Z"
  }
}
```

消费者读取时先检查 `meta.version`，使用对应版本的校验逻辑。

---

## 5. 版本管理与向后兼容

### 版本升级规则

- **v1→v2**：只允许**添加**新字段（optional），不允许删除或修改已有字段
- **v1→v2**：如果必须修改已有字段 → 创建新流（如 `ec-sourcing-to-listing-v2`）
- 版本号记录在 schema 文件的 `version` 字段

### 消费者兼容策略

```
读取数据 → 检查 meta.version
  ├─ v1 → 用 v1 schema 校验
  └─ v2 → 用 v2 schema 校验，v1 字段必须有默认值/降级逻辑
```

---

## 6. 数据写入与消费模式

### 生产者写入

```bash
# 写入示例 (DS-01: finance → writer)
cat signal_data.json > ~/.hermes/bus/quant-signal-to-writer/2026-05-11.json
```

### 消费者读取

两种模式：

1. **kanban context_from** — 用于串行 pipeline 场景，上游任务完成后下游自动读取
2. **直接文件读取** — 用于独立任务，消费者通过 cron/agent 定期扫描总线目录

---

## 7. EC 三域遗留兼容

原有 `~/PDD/商品/{YYYY-MM-DD}/{商品名}/listing-ready/listing.json` 路径继续可用（v1 格式）。
新 v2 格式写入 `~/.hermes/bus/ec-sourcing-to-listing/`，EC 消费者应同时支持两种路径。

| 版本 | 路径 | 特征 |
|:----|:----|:----|
| v1 (遗留) | `~/PDD/商品/{date}/{name}/listing-ready/listing.json` | 无 meta 段，业务字段直接顶层 |
| v2 (新) | `~/.hermes/bus/ec-sourcing-to-listing/{date}-{no}.json` | 有标准 meta，JSON Schema 校验 |

---

## 8. 版本历史

| 版本 | 日期 | 变更 |
|:----|:----|:-----|
| v2 | 2026-05-11 | 全域扩展：新增4个数据流(DS-01~04, DS-06)，EC契约升级v2，目录标准化 |
| v1 | 2026-04-28 | 初始版（EC三域：sourcing→listing→fulfillment） |
