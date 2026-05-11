# A股量化系统设计研究 (2026-05-01)

> 深度研究产出，位于 `~/research-skill-graph/projects/quant-system-design/`

## 核心结论

四层信号叠加系统：基本面(35%) + 缠论二买(25%) + 量价智能(20%) + 共振(20%)

基线: mid-cap-multi-factor v2.1 (年化28.35%, 夏普1.54, 最大回撤8.08%)
预期: 保守年化32-38%, 夏普1.6-1.8

## 关键已验证发现

### Layer 2 缠论二买 (IC +0.137, 胜率63.7%)
- 一买仅做前置条件，不独立入场
- 二买是唯一统计显著的入场信号
- 三买衰减快、卖点反效果 (IC -0.049)

### Layer 3 数据源替换
- 东方财富"主力净流入"已证伪 (BigQuant -45.94%)
- 改用 K线自算: OBV/MFI/VWAP/KAMA/POS

### 主流量化平台参考
- BigQuant StockRanker + 因子工厂 (AI驱动)
- JoinQuant 最佳多因子+ML策略 年化87-103% (回撤22-30%)
- 中欧量化"三元低相关"策略 (基本面/量价/深度学习)

## 实施产物

| 文件 | 路径 | 用途 |
|:-----|:-----|:-----|
| chan_buy_signal.py | ~/quant/ | Layer 2 缠论二买 (纯pandas, 无czsc依赖) |
| volume_indicators.py | ~/quant/ | Layer 3 量价指标 |
| signal_engine.py | ~/quant/ | 四层信号合成引擎 |

## 相关 wiki 条目

- `知识库/concepts.md`: 缠论, 量价, StockRanker, 三元低策略, RSRS, 四层信号系统等
- `知识库/data-points.md`: 东北证券32指标, chan.py 1700星, 缠论误判率37%等
