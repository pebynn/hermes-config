# ============================================================
# T3 审查报告 — 动量策略回测结果 (T2)
# 审查日期: 2026-05-13
# 审查人: reviewer (t_190a2d5a)
# 审查对象: /home/pebynn/quant/backtest_momentum.csv
# ============================================================

## 最终判定: FAIL

原因: 硬止损使用公式化出场价（128/132笔=97%精确-8.0%），系统性低估真实亏损；
      年化收益95.5%（TOP_N=5）或183.5%（TOP_N=3），均未达300%目标。

---

## 审查清单逐项结果

### 1. 数据源准确性 — FAIL (BLOCKED)

**问题1 (CRITICAL)**: Sina Parquet列名bug
- `load_data_sina()` 第153行: `df.rename(columns={"date":"日期",...})`
- Sina Parquet 实际列名: `trade_date`（不是 `date`）
- 后果: 重命名失败 → KeyError on `df['日期']` → 无法完成双源交叉验证
- MySQL路径正常（`load_data_mysql()` 正确映射 `trade_date`→`日期`）

**问题2 (WARNING)**: Sina Parquet仅含100只股票（vs MySQL 5308只），即使修复后参考价值有限。

**建议**: 
```python
date_col = 'trade_date' if 'trade_date' in df.columns else 'date'
df = df.rename(columns={date_col: "日期", ...})
```

---

### 2. 未来函数检测 — PASS ✅

代码设计正确，无前视偏差：
- 因子排名: `panel.xs(all_dates_list[cur_idx-1])` — 使用**昨日**因子（v1 L183-188, v2 L211-216）
- 入场价格: `float(row['开盘'])` — **当日开盘价**（v1 L272, v2 L313）
- 出场检测: 使用当日 `day_low`/`day_high` 判断止损/止盈触发条件（v1 L196-201, v2 L224-233）
- 因子计算: 仅基于历史数据，无可疑未来引用

结论: 因子计算、排名、入场、出场触发条件均不存在前视偏差。

---

### 3. 杠杆检查 — PASS ✅

- v1: `LEVERAGE = 1.0`（L25）
- v2: `LEVERAGE = 1.0`（L25）
- 未使用融资/融券/期货杠杆

结论: 无杠杆风险。

---

### 4. 胜率计算 — PASS ✅

独立验证结果（324笔交易）:
```
Wins:   145 (pnl > 0)
Losses: 173 (pnl < 0)
Ties:     6 (pnl = 0)
Win Rate (wins/total): 44.75%
Win Rate (wins/(wins+losses)): 45.60%
```

公式 `wins/total * 100` 计算正确。胜率在可接受范围但略低于45-55%目标区间。

---

### 5. 年化收益公式 — FORMULA CORRECT, PARAMETER MISMATCH ⚠️

**公式本身正确**:
```python
cumulative_ret = 1.0
for each trade: cumulative_ret *= (1 + pnl_pct/100 / TOP_N)
annualized = (cumulative_ret ** (1/years) - 1) * 100
```

**但有2个问题**:

**问题1**: `analyze_backtest.py` 使用 TOP_N=5，但回测周期仅覆盖2026-01-01→2026-04-30（119天），忽略2025-05-07→2025-12-31的数据。

**问题2**: `reconstruct_nav.py` 硬编码 `TOP_N=5`（L13），但策略v2使用 `TOP_N=3`。TOP_N不匹配导致年化收益计算偏差。

独立验证（全周期 2025-05-07 → 2026-04-30，358天）:
| TOP_N | 总收益 | 年化收益 |
|-------|--------|----------|
| 5 (v1假设) | 92.89% | 95.48% |
| 3 (v2假设) | 177.70% | 183.51% |

无论哪种假设，均未达到300%年化目标。

---

### 6. 交易合理性 — FAIL 🔴

**严重问题: 硬止损出场价使用公式而非实际市场价**

v1代码L244 / v2代码L280:
```python
exit_px = pos['entry_price'] * (1 - HARD_STOP)  # 公式价
```

验证数据:
- 132笔硬止损中，128笔（97.0%）精确 = -8.00%
- 其余4笔: -7.90%, -7.71%, -7.46%, -5.78%（疑似代码版本差异导致）
- **这不是真实市场行为** — 实际止损触发时滑点/跳空会使亏损 >= HARD_STOP

止损检测条件（L200, L232）正确使用了 `day_low`，但出场价仍用公式:
```python
# 检测: if day_low <= stop_price → 正确
# 出场: exit_px = ep * (1-HARD_STOP) → 错误，应用 day_low
```

同样问题存在于移动止盈出场价（v1 L246, v2 L282）:
```python
exit_px = high_c * (1 - TRAILING_DISTANCE)  # 公式价而非 day_low
```

**修复建议**:
```python
# 硬止损
exit_px = day_low  # 使用实际触发价
# 或保守估计
exit_px = min(day_low, ep * (1 - HARD_STOP))

# 移动止盈
exit_px = min(day_low, high_c * (1 - TRAILING_DISTANCE))
```

---

### 7. 存活偏差 — WARNING ⚠️

- 股票池筛选仅用 `len(grp) >= 60`（v1 L151, v2 L178）
- 未显式检查退市日期 → 可能包含已退市股票的历史数据
- MySQL `kline` 表可能包含已退市股票（交易时它们仍在市场中，合理；但应从退市日起移除）

**建议**: 在 universe 构建阶段加入退市日期过滤。

---

### 8. 分析脚本问题 — MEDIUM ⚠️

`reconstruct_nav.py` (T2 workspace):
- L13: `TOP_N = 5` 硬编码 — 应与策略配置一致（v2=3, v1=5）
- L11-12: 仅分析 2026-01-01→2026-04-30，忽略前半段数据
- L19: `str(int(x)).zfill(6)` 对600643等代码可能截断

`analyze_backtest.py` (T2 workspace):
- L119: `TOP_N` 变量未定义 → 会在NAV重建路径抛出 NameError
- 同类窗口截断问题

---

## 完整问题列表

| # | 严重度 | 类别 | 问题 |
|---|--------|------|------|
| 1 | 🔴 CRITICAL | 数据准确性 | 硬止损使用公式出场价 `ep*(1-HARD_STOP)` 而非 `day_low`，128/132笔精确-8% |
| 2 | 🔴 CRITICAL | 目标 | 年化收益95.5-183.5%，均未达300%目标 |
| 3 | 🟡 HIGH | 数据管道 | `load_data_sina()` 列名bug — 无法完成双源交叉验证 |
| 4 | 🟡 HIGH | 数据准确性 | 移动止盈出场价同样使用公式价而非 `day_low` |
| 5 | 🟡 MEDIUM | 指标计算 | `analyze_backtest.py` 中TOP_N硬编码与策略配置不匹配 |
| 6 | 🟡 MEDIUM | 分析完整性 | 分析脚本仅覆盖4个月，忽略8个月数据 |
| 7 | 🟢 LOW | 存活偏差 | 股票池未显式过滤已退市股票 |

---

## 审核元数据

- 回测文件: /home/pebynn/quant/backtest_momentum.csv
- 回测周期: 2025-05-07 → 2026-04-30 (358天, 0.98年)
- 策略文件: strategy_momentum.py (v1) / strategy_momentum_v2.py (v2)
- 数据源: MySQL kline (5308只), Sina Parquet (100只, 不可用)
- 总交易: 324笔 | 胜率: 44.75% | 盈亏比: 1.31
- 硬止损: 132笔 (40.7%), 移动止盈: 102笔 (31.5%), DROP: 87笔 (26.9%), 强制平仓: 3笔 (0.9%)
- 关键参数: TOP_N未知(3或5), HARD_STOP=8%(推断), 无杠杆
- Sina交叉验证: BLOCKED (列名bug)
