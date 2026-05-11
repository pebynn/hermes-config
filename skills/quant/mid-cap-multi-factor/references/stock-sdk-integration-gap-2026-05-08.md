# stock-sdk 未集成分析 — 2026-05-08

## 现状

stock-sdk MCP (Node.js, 50+ tools) 已全局安装于 `/home/pebynn/.hermes/node/bin/stock-mcp`, 已验证可用：
- 个股日K线 5914行(23年)
- 分钟K线(5/15/30/60)
- 行业板块K线+成分股
- 概念板块K线
- 资金流排名/历史
- 北向个股持仓排名
- 龙虎榜+席位明细
- 涨停池6大股池
- 批量20只行情 ~327ms

## 信号引擎当前使用的数据源

| 层 | 数据 | 当前来源 | stock-sdk可替代? |
|:--|:----|:---------|:----------------|
| L1 | K线 | parquet/MySQL | 可做交叉验证 |
| L1 | 财务 | parquet (同花顺THS) | 无 |
| L1 | 行业 | tushare申万110 | 无 |
| L1 | 总股本 | share_db.parquet | 无 |
| L2 | 缠论二买 | K线自算 | — |
| L3 | 量价指标 | K线自算(OBV/MFI/VWAP/KAMA) | — |
| L4 | 两融 | AKShare SSE+SZSE | 无 |
| L5 | **资金流** | **空** | ✅ getFundFlowRank + 历史 |
| L5 | **北向个股** | **空** (AKShare全失效) | ✅ getNorthboundHoldingRank |
| L5 | **龙虎榜** | **空** | ✅ getDragonTigerList |
| L5 | **涨停池** | **空** | ✅ getZTPool(6种) |
| — | **分钟K线** | **无** | ✅ 5/15/30/60分钟 |
| — | **概念板块** | **无** | ✅ 概念K线+成分股 |

## 集成方向（待决策）

### 方案A: 信号引擎加 Layer 5
- signal_engine.py 新增 `_compute_layer5()` 调 stock-sdk SDK
- 资金流+北向+龙虎榜+涨停态 → 4维评分 → 乘数调整 composite
- 优势: 统一评分框架, 一次扫描全量
- 风险: signal_engine 已 >1100行, 再加layer更臃肿

### 方案B: 独立短/中线策略管道
- 独立的 `mid_cap_shortterm.py` 用 stock-sdk 资金流/龙虎榜/涨停池
- 与现有 signal_engine 互补: 短线(日频) + 中线(周频)
- 优势: 职责分离, 不相互影响
- 风险: 两套策略需要协调仓位

### 方案C: 先接入部分信号 (最小成本验证)
- 只接涨停池(boolean flag) + 资金流排名(0-100分)
- 作为现有composite的额外加分项(×1.05~1.15)
- 优势: 1天可完成, 验证信号有效性
