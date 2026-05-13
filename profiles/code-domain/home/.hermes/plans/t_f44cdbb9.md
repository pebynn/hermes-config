# R1-B-代码优化 — 实施计划

**任务ID**: t_f44cdbb9
**日期**: 2026-05-13
**策略**: Strategy B-R9 Reversal → R1 优化
**目标**: 年化 300%+, 胜率 45-55%, LEVERAGE=1.0

---

## Step 1: Brainstorming — 设计方案

### 1.1 当前代码审计 (strategy_reversal.py, 621行)

| 参数 | docstring声称 | 代码实际值 | 差异 |
|------|-------------|-----------|------|
| DECLINE_PREFILTER | -4% (ret_5d < -4%) | -0.035 (-3.5%) | docstring过时, 代码已是-3.5% |
| SECTOR_HEAT_HARD_FILTER | 0.55 | 0.55 | 一致 |
| MAX_POSITIONS | 12 | 12 | 一致 |
| TAKE_PROFIT | 13% half | 0.13 | 一致 |
| LEVERAGE | 1.0 | 1.0 | ✅ 铁律满足 |
| OUTPUT_FILE | - | backtest_reversal.csv | 需改为 backtest_B.csv |
| 回测周期 | 2025-05→2026-04 | 2025-05-01→2026-04-30 | ✅ 完整12个月 |
| REBALANCE_DAYS | 3 | 3 | 一致 |
| STOP_LOSS | 8% | -0.08 | 一致 |
| TRAILING_STOP_PCT | 6% | -0.06 | 一致 |
| TIME_STOP | 3d + ret<-3% | 3d + -0.03 | 一致 |

### 1.2 R9代码完整性检查

回测周期检查: mask = (df["trade_date"] >= START_DATE) & (df["trade_date"] <= END_DATE) — ✅ 完整周期
未来函数检查: 所有因子 lagged 1d (shift(1)), sector_heat_cache 也 shifted — ✅ 无未来函数
数据源: fallback_resolver.load_kline() (MySQL→Sina) — ✅ 符合铁律

### 1.3 修改方案选择

**方案A（激进）**: 仅修改5个参数，保持R9核心逻辑不变
**方案B（保守）**: 修改参数 + 增加额外筛选逻辑
**方案C（回退）**: 回退到R8基线再修改

→ **选择方案A** — 任务明确了5个修改方向，R9逻辑核心（宽进严选+板块过滤+动态仓位）已证明合理，问题在于参数调优而非逻辑重构。

### 1.4 具体修改

| # | 位置 | 修改项 | 前值 | 后值 | 理由 |
|---|------|-------|------|------|------|
| 1 | L56 | MAX_POSITIONS | 12 | 15 | 更分散风险，增加候选覆盖率 |
| 2 | L76 | DECLINE_PREFILTER | -0.035 | -0.03 | 放宽入场池 (-3.5%→-3%)，更多候选 |
| 3 | L75 | SECTOR_HEAT_HARD_FILTER | 0.55 | 0.50 | 降低板块门槛，减少误杀 |
| 4 | L58 | TAKE_PROFIT | 0.13 | 0.10 | 更早止盈，提高胜率 (13%→10%) |
| 5 | L61 | OUTPUT_FILE | backtest_reversal.csv | backtest_B.csv | 任务要求 |
| 6* | L599 | trades_path | backtest_reversal_trades.csv | backtest_B_trades.csv | 一致性 |
| 7* | L601 | nav_path | backtest_reversal_nav.csv | backtest_B_nav.csv | 一致性 |

*#6-7: 附带的输出文件命名一致性修改

### 1.5 替代方案（未选择）

- **替代A**: 同时修改REBALANCE_DAYS从3→2 — 增加交易频率但可能过度交易
  - 未选择原因: 任务未提及，R9设计明确3天周期
- **替代B**: 增加动态TAKE_PROFIT (基于vol_20d) — 更复杂
  - 未选择原因: 超出R1范围，应留到R2

### 1.6 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| -3%预过滤引入过多噪音股 | 中 | 胜率下降 | sector_boost 0.50+ 板块过滤会兜底 |
| 10% TP过早止盈损失复利 | 中 | 总收益降低 | trailing_stop保留剩余仓位 |
| MAX_POSITIONS=15资金分散 | 低 | 集中度下降 | 动态仓位仍会给强信号更大权重 |

---

## Step 2: Writing Plans — 实施步骤

### 2.1 文件变更清单

单文件修改: `/home/pebynn/quant/evo_optimizer/strategy_reversal.py`

变更点:
- L56: `MAX_POSITIONS = 12` → `15`
- L58: `TAKE_PROFIT = 0.13` → `0.10`
- L61: `OUTPUT_FILE = ".../backtest_reversal.csv"` → `".../backtest_B.csv"`
- L75: `SECTOR_HEAT_HARD_FILTER = 0.55` → `0.50`
- L76: `DECLINE_PREFILTER = -0.035` → `-0.03`
- L599: trades_path 含 backtest_reversal → backtest_B
- L601: nav_path 含 backtest_reversal → backtest_B
- L560-570: 打印信息中的参数值字符串更新
- L10, L18, L19, L561, L568-574: docstring 和打印信息更新

### 2.2 验证计划

1. `python3 -m py_compile strategy_reversal.py` — 语法检查
2. grep LEVERAGE=1.0 — 确认杠杆不变
3. grep OUTPUT_FILE — 确认输出路径正确
4. 视觉审查所有修改的diff
