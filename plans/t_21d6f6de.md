# 策略C — 初版适配运行 Plan

## 元信息
- Task: t_21d6f6de
- 目标: 策略C代码修复，确保 2026-01-06~2026-05-13 回测可启动
- 日期: 2026-05-13

---

## 1. 架构分析

### 导入链
```
strategy.py (strategies/strategy_c_policy/)
  ├── from shared.backtest_engine import BacktestEngine  → /home/pebynn/quant/shared/backtest_engine.py ✓
  ├── from shared.data_loader import DataLoader           → /home/pebynn/quant/shared/data_loader.py ✓
  ├── from shared.factor_lib import FactorLib             → /home/pebynn/quant/shared/factor_lib.py ✓
  ├── from shared.risk_manager import RiskManager         → /home/pebynn/quant/shared/risk_manager.py ✓
  └── from data_common import ...                         → /home/pebynn/quant/data_common.py ✓
```
**注意**: strategy_c_policy/shared/ 下的 backtest_engine.py 是**旧版stale副本**，不会被导入。实际导入的是 `/home/pebynn/quant/shared/backtest_engine.py`。

### BacktestEngine 接口
- 子类必须实现: `_select_stocks(xsec_rank, positions)` 和 `_should_exit(code, position, current_data)`
- StrategyC 已实现这两个方法 ✓

### 回测主循环 (run方法)
1. 加载K线 → DataLoader.load_kline()
2. 加载资金流 → DataLoader.load_fund_flow_range()
3. 构建因子面板 → FactorLib.build_factor_panel()
4. 日循环:
   a. 月度空仓检查 → RiskManager.is_empty_month() — strategy C empty_months=[] → 永远false ✓
   b. 获取昨日因子排名 → xsec_rank
   c. 退出检查 → _should_exit() (止损/资金流连续流出)
   d. 组合止损 → RiskManager.check_portfolio_stop()
   e. 调仓日 → RiskManager.is_rebalance_day() — 检查dayofweek
   f. 选股入场 → _select_stocks() (月度概念选股 + 资金流评分)
   g. NAV计算 (prev_close方法)
5. 强制平仓
6. 生成报告

### 关键发现/问题

#### ✅ 已确认正常
- 所有模块导入通过
- Sina parquet 存在 (31961行, 100只股票, 320个交易日)
- 语法检查通过

#### ⚠️ 问题1: 数据截止日期
- Sina parquet 数据到 2026-04-30，请求 2026-05-13 超出范围
- **方案**: 先尝试 MySQL (可能有更多数据)，回退到 Sina 用 2026-04-30

#### ⚠️ 问题2: 调仓频率不匹配
- STRATEGY_C_CONFIG 设置 `rebalance_weekly: False` (月度调仓)
- 但 RiskManager.is_rebalance_day() 不检查 rebalance_weekly 标志
- BacktestEngine.run() 直接调用 `self.risk_mgr.is_rebalance_day(cur_date)` — 每周一都会调仓
- **影响**: 策略C的月度概念选股只在月份变化时执行，但每周一都会重新选股(从_stock_pool中按fund_flow_score选)。实际上不会破坏逻辑，因为概念选股有月份缓存。
- **方案**: 保持现状，月度概念切换+每周调仓不冲突

#### ⚠️ 问题3: _get_current_month 依赖 nav_series
- `_get_current_month()` 从 `self.nav_series` 最后一条记录推断日期
- 但 nav_series 在 `_select_stocks` 调用前可能已更新或为空
- 如果为空的第一次调用会返回 `""` 触发 `_monthly_concept_selection()`
- MCP 概念加载在回测环境中可能不可用 → 回退到全量股票池
- **方案**: 只要 MCP 失败回退正常，不影响运行

#### ⚠️ 问题4: 回退路径依赖 fund_flow_score 列
- 当 stock_pool 为空时，_select_stocks 回退到 `xsec_rank.nlargest(top_n, "fund_flow_score")`
- 需要确认 FactorLib 在 panel 中包含 fund_flow_score 列
- **方案**: 验证 FactorLib.build_factor_panel 输出

---

## 2. 执行计划

### 第3步: TDD — 写测试
- 写最小化冒烟测试: 验证 StrategyC 可实例化 + run() 不崩溃
- 预期 RED (因为数据/运行问题)

### 第4步: 编码修复
- **必须修复**: 确保 `--end 2026-05-13` 时能有数据 (调整end到实际数据范围或提示)
- **可能修复**: 如果资金流数据不可用，确保回退路径有效
- **可能修复**: 因子面板列匹配

### 第5步: 调试
- 运行 strategy.py，收集所有错误
- 逐一修复

### 第6步: 自审
- 代码正确性
- 策略逻辑合理性

### 第7步: 验证
- `python3 strategy.py --source sina --start 2026-01-06 --end 2026-04-30` 完整运行
- 检查 output/ 目录产出

---

## 3. 设计方案

### 方案选择: 最小改动 + 健壮回退

不重写策略逻辑，只修复阻碍运行的bug：

1. **数据截止自适应**: main() 中添加数据可用性检测，自动调整 end_date 不超过数据最后日期
2. **资金流回退**: 如果 load_fund_flow_range 返回空 → FactorLib 使用无资金流模式 → 因子面板仍可构建
3. **MCP回退**: 已存在 try/except 包裹，确认回退路径不抛异常

### 替代方案 (不采用)
- 重写 MCP 调用逻辑使用本地数据 → 改动太大，风险高
- 新增概念动量缓存 → 超出初版适配范围

### 风险
- 中: 100只股票池可能过小导致无交易
- 低: 因子计算可能因列名不匹配失败
