---
allowed-tools:
- read_file
- write_file
- terminal
author: ops-domain
category: development
description: 全域跨域数据总线 — 定义6条标准化数据契约，覆盖 finance→writer / research→graphify / reviewer→writer / ops→code / EC三域
name: pipeline-bus
version: 2.0.0
when-to-use: 跨域传递数据时、开发/修改域间接口时、新增模块对接已有时 特别在 delegate_task 跨域传 context 时，用本契约规范字段名
---

# Pipeline Bus — 全域数据总线

## 概述

将原先仅覆盖 EC 三域（sourcing→listing→fulfillment）的数据总线扩展为覆盖所有域的全域总线。

```
                            ┌─────────────────────────┐
                            │     Hermes 全域数据总线     │
                            │   ~/.hermes/bus/          │
                            └─────────────────────────┘
                                     │
          ┌──────────┬──────────┬────┴────┬──────────┬──────────┐
          ▼          ▼          ▼         ▼          ▼          ▼
       DS-01      DS-02      DS-03     DS-04      DS-05      DS-06
    finance→    research→  reviewer→  ops→      sourcing→  fulfillment→
    writer     graphify    writer     code      listing     sourcing
```

## 数据流总表

| ID | 数据流 | 生产者 | 消费者 | Schema文件 | 版本 |
|:---|:-------|:-------|:-------|:-----------|:----|
| DS-01 | 量化信号→写作素材 | finance-domain | writer | `~/.hermes/bus/schema/quant-signal-to-writer.json` | v1 |
| DS-02 | 调研结果→知识图谱 | research-domain | graphify | `~/.hermes/bus/schema/research-to-graphify.json` | v1 |
| DS-03 | 审查反馈→写作改进 | reviewer | writer | `~/.hermes/bus/schema/reviewer-to-writer.json` | v1 |
| DS-04 | 故障诊断→代码修复 | ops-domain | code-domain | `~/.hermes/bus/schema/ops-to-code.json` | v1 |
| DS-05 | EC选品→上架 | ec-sourcing | ec-listing | `~/.hermes/bus/schema/ec-sourcing-to-listing.json` | v2 |
| DS-06 | EC运营→选品调整 | ec-fulfillment | ec-sourcing | `~/.hermes/bus/schema/ec-fulfillment-to-sourcing.json` | v1 |

---

## 统一元信息结构

所有数据流共享 `meta` 字段：

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

消费者在读取时**必须先检查 `meta.version`**，使用对应版本的校验逻辑。

---

## DS-01: 量化信号 → 写作素材

### 路径约定

```
~/.hermes/bus/quant-signal-to-writer/{YYYY-MM-DD}.json
```

### 核心字段

```json
{
  "meta": { "stream": "quant-signal-to-writer", "version": "v1", "producer": "finance-domain", "consumer": "writer" },
  "summary": {
    "market_mood": "bearish",      // bullish / bearish / neutral / mixed
    "overall_assessment": "今日A股缩量下跌...",
    "key_signals_count": 8
  },
  "signals": [
    {
      "id": "sig-001",
      "type": "technical",         // technical / fundamental / sentiment / macro / policy / sector
      "ticker": "000001",
      "title": "上证指数跌破20日均线",
      "description": "上证指数今日收盘...",
      "direction": "negative",     // positive / negative / neutral
      "confidence": 0.78,
      "urgency": "high"
    }
  ],
  "charts": [
    { "title": "上证日K", "type": "kline", "description": "...", "file_path": "/path/to/chart.png" }
  ],
  "recommended_sections": [
    { "section": "盘面综述", "focus": "缩量下跌原因分析", "signal_ids": ["sig-001", "sig-002"] }
  ]
}
```

---

## DS-02: 调研结果 → 知识图谱

### 路径约定

```
~/.hermes/bus/research-to-graphify/{YYYY-MM-DD}-{topic}.json
```

### 核心字段

```json
{
  "meta": { "stream": "research-to-graphify", "version": "v1", "producer": "research-domain", "consumer": "graphify" },
  "entries": [
    {
      "id": "entry-001",
      "type": "concept",        // concept / fact / insight / relation / source / conclusion
      "title": "中老年女装2026趋势",
      "summary": "宽松显瘦版型持续走俏...",
      "detail": "详细内容...",
      "tags": ["中老年女装", "2026趋势", "电商"],
      "confidence": 0.85,
      "sources": [
        { "url": "https://...", "title": "来源标题", "reliability": "high" }
      ],
      "relations": [
        { "target_id": "entry-002", "relation_type": "supports" }
      ]
    }
  ]
}
```

---

## DS-03: 审查反馈 → 写作改进

### 路径约定

```
~/.hermes/bus/reviewer-to-writer/{YYYY-MM-DD}-{article}.json
```

### 核心字段

```json
{
  "meta": { "stream": "reviewer-to-writer", "version": "v1", "producer": "reviewer", "consumer": "writer" },
  "overall_assessment": {
    "score": 7,
    "verdict": "approve_with_changes",   // approve / approve_with_changes / rework / reject
    "summary": "总体质量不错，但数据引用需核实"
  },
  "issues": [
    {
      "id": "iss-001",
      "category": "factual",        // accuracy / clarity / style / structure / factual / compliance / formatting
      "severity": "major",          // critical / major / minor / suggestion
      "location": "第二段",
      "original_text": "上证指数上涨5%",
      "description": "数据有误，实际涨幅为3.2%",
      "suggestion": "更正为3.2%",
      "suggested_replacement": "上证指数上涨3.2%"
    }
  ],
  "action_items": [
    { "priority": "must_fix", "action": "核实第二段数据引用", "issue_ids": ["iss-001"] }
  ]
}
```

---

## DS-04: 故障诊断 → 代码修复

### 路径约定

```
~/.hermes/bus/ops-to-code/{incident_id}.json
```

### 核心字段

```json
{
  "meta": { "stream": "ops-to-code", "version": "v1", "producer": "ops-domain", "consumer": "code-domain" },
  "symptoms": [
    { "indicator": "cron_uptime", "expected": "7d", "actual": "2h", "detail": "cron反复重启" }
  ],
  "root_cause": {
    "summary": "config.yaml语法错误导致解析失败",
    "category": "config_error",
    "affected_files": ["~/.hermes/config.yaml"]
  },
  "fix_recommendations": [
    {
      "priority": 1,
      "title": "修复YAML缩进",
      "description": "第42行缩进不一致，需修复",
      "risk": "low"
    }
  ]
}
```

---

## DS-05: EC选品 → 上架 (v2 升级版)

### 路径约定

| 版本 | 路径 |
|:----|:-----|
| v1 (遗留) | `~/PDD/商品/{YYYY-MM-DD}/{商品名}/listing-ready/listing.json` |
| v2 (新) | `~/.hermes/bus/ec-sourcing-to-listing/{YYYY-MM-DD}-{goods_no}.json` |

### 向后兼容

消费者（ec-listing）必须同时支持 v1 和 v2 格式：
- v1: 无 `meta` 段，字段在顶层，以 `goods_name` 等直接命名
- v2: 有标准 `meta` 段，业务字段封装在 `goods_info` 下

```json
{
  "meta": { "stream": "ec-sourcing-to-listing", "version": "v2", "producer": "ec-sourcing", "consumer": "ec-listing" },
  "goods_info": {
    "goods_name": "中老年妈妈夏装宽松显瘦连衣裙",
    "cat_id": null,
    "market_price": 11900,
    "goods_price": 7990,           // 单位：分
    "goods_number": 24000,
    "main_images": ["/path/main.jpg"],
    "detail_images": ["/path/detail.jpg"],
    "sku_list": [
      { "spec": "黑色,L", "price": 7990, "quantity": 1000 }
    ],
    "out_goods_id": "SH001"
  },
  "pricing": {
    "tier": "profit",
    "cost_price": 35,
    "suggested_price": 87.5,
    "estimated_profit": 30.18
  },
  "source": {
    "shop_name": "卡彤网批",
    "goods_no": "SH001"
  }
}
```

### 定价策略参考
- 引流 1.3x / 利润 1.5x / 形象 1.8x
- 退货率 20%
- `goods_price` 单位：**分**（PDD API 要求）
- 主图最多 5 张
- SKU：颜色×尺码笛卡尔积，均码展开 L/XL/2XL/3XL/4XL/5XL

---

## DS-06: EC运营 → 选品调整

### 路径约定

```
~/.hermes/bus/ec-fulfillment-to-sourcing/{YYYY-MM-DD}-{period}.json
```

### 核心字段

```json
{
  "meta": { "stream": "ec-fulfillment-to-sourcing", "version": "v1", "producer": "ec-fulfillment", "consumer": "ec-sourcing" },
  "overview": {
    "total_orders": 150,
    "total_returns": 30,
    "return_rate": 0.20,
    "avg_dsr": 4.2
  },
  "product_feedback": [
    {
      "goods_name": "中老年妈妈夏装...",
      "out_goods_id": "SH001",
      "orders": 50,
      "returns": 12,
      "return_rate": 0.24,
      "dsr": 3.8,
      "common_complaints": ["尺码偏小", "颜色色差"],
      "suggestion": "adjust_price"
    }
  ],
  "sourcing_recommendations": [
    { "type": "discontinue", "reason": "退货率超30%", "target_goods": "SH002", "urgency": "immediate" }
  ]
}
```

---

## 参考文件

- `references/kline-schema.md` — stock_kline.kline 表完整Schema，含 total_mv 计算、amount≠总市值混淆、MySQL约束 (2026-05-14)

## 版本记录

| 版本 | 日期 | 变更 |
|:----|:----|:-----|
| 2.0.0 | 2026-05-11 | 全域扩展：新增 DS-01~04, DS-06，EC 契约升级 v2，统一 meta 结构 |
| 1.0.0 | 2026-04-28 | 初始版（EC 三域: sourcing→listing→fulfillment） |
