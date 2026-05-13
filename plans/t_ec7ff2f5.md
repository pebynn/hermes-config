# R3 Implementation Plan — A-R3-OOS修复-消除未来函数v2
Task: t_ec7ff2f5 | Date: 2026-05-13
File: /home/pebynn/quant/strategies/strategy_a_momentum/strategy_v2.py

## 背景

策略A v2 OOS验证发现4个未来函数偏差(lookahead bias):
1. check_momentum_entry() 用当日收盘判断当日开盘入场 → lookahead
2. 移动止盈触发后用当日开盘价执行 → A股T+1不能当日卖出
3. 全局T+1约束: 买入日与卖出日不能相同
4. 跌停板滑点: 止损在跌停板无法平仓时应记入次日开盘

R2的5个运行时参数不变: stop_loss=0.10, trailing_stop=0.06, portfolio_stop=0.15, ic_window=20, ic_temperature=2.0

## 现有状态分析

### 已完成的R3修改 (部分正确):
- check_momentum_entry(): ✅ 已改为使用xr的mom因子(10日收益率)，消除lookahead
- is_limit_down(): ✅ 新函数，检测主板10%跌停
- Buy逻辑: ✅ 传入xr.loc[c]而非xt.loc[c]
- T+1检查: ✅ 在hard stop(st)和trailing stop(st_next)中已添加
- pending_exits机制: ✅ 初始化 + 次日开盘处理框架(line 302, 369-382)

### 存在的BUG (4个需修复):

**BUG-1 [CRITICAL]: pending_exit vs pending_exits 变量混淆**
- Line 302: `pending_exits = {}` (正确初始化)
- Line 350: `if pending_exit:` — 引用不存在的local变量 pending_exit (NameError at runtime)
- Lines 351-361: 处理 pending_exit 的退出逻辑 — 这个block与lines 369-382的pending_exits处理**重复**
- Lines 443-444: `pending_exit = {}; pending_exit[c] = p` — 创建local变量，不会影响全局pending_exits
- **修复**: 删除lines 350-361重复block。将line 443-445改为向pending_exits添加。

**BUG-2 [CRITICAL]: 硬止损跌停处理使用当日收盘而非延期**
- Lines 430-438: 检测到跌停后仍使用`收盘*0.985`立即退出
- 应改为: 跌停时加入pending_exits，次日开盘退出
- **修复**: 跌停分支 → `pending_exits[c] = {"ep": p["ep"], "in": p["in"], "reason": "stop_limit_down"}`

**BUG-3 [HIGH]: 硬止损非跌停情况也应使用收盘价更保守**
- Line 436: `xp = float(xt.loc[c,"收盘"])` — 当前用收盘价(正确，非lookahead)
- 但可以对非跌停硬止损加0.5%滑点: `xp = close * 0.995`
- **修复**: 添加滑点系数

**BUG-4 [MEDIUM]: portfolio_stop和drop退出缺少T+1检查**
- Lines 447-456: ps_hit和drop两条退出路径没有检查 `pos[c].get("in") == cd`
- 虽然调仓日在周一(非买入日通常不会冲突)，但di==0时可能同一天买入又卖出
- **修复**: 添加T+1跳过逻辑，若同一天则推迟到pending_exits

## 修改方案

### 方案选择: 统一pending_exits机制

所有延期退出(跌停硬止损、移动止盈、T+1冲突)统一使用`pending_exits`字典:

```
pending_exits = {code: {"ep": entry_price, "in": entry_date, "reason": str}}
```

每个交易日开始时(获取xt之后, 止损检查之前):
1. 遍历pending_exits，用当日开盘价执行退出 → 记录trade
2. 清空pending_exits

止损检查时:
- 硬止损触发 + 跌停 → pending_exits (reason='stop_limit_down')
- 硬止损触发 + 非跌停 → 当日收盘 * 0.995 立即退出 (reason='stop')
- 移动止盈触发 → pending_exits (reason='trail')
- 当日买入(T+1) + 任何退出信号 → pending_exits (reason按原类别)

### 替代方案(否决):
- 用两个独立dict(trail_pending, stop_pending): 增加复杂度，无收益
- 当日立即记录trade然后从pos移除: 违背T+1规则

### 风险:
- 延期退出可能导致持仓数超过TOP_N_V2(因为新买入+pending持仓共存)
  → 缓解: pending_exits中的持仓已从pos移除，不参与NAV计算
- 连续跌停: pending_exit可能在下一个交易日仍无法退出
  → 缓解: 异常处理中xt.index缺失→用universe最后收盘价退出

## 实施步骤

1. **删除** lines 349-361 (重复的pending_exit处理block)
2. **修改** Sell section (lines 420-457):
   - Hard stop非跌停: 收盘*0.995立即退出
   - Hard stop跌停: 加入pending_exits
   - Trailing stop: 加入pending_exits (修复变量混淆)
   - Portfolio stop: 添加T+1检查
   - Drop: 添加T+1检查
3. **验证** pending_exits处理逻辑(line 369-382)正确
4. **确认** end-close (line 513-519) 也处理pending_exits中的残留

## 测试策略

现有32 test全部PASS。需要:
- test_check_momentum_entry_*: 8个test ✅ already pass (R3 fix validated)
- test_t1_constraint_*: 2个纯逻辑test ✅ pass (需确认实现匹配)
- test_limit_down_*: 2个纯逻辑test ✅ pass
- test_pending_exits_*: 3个结构test ✅ pass

**新增测试** (TDD Step 3):
- test_hard_stop_non_limitdown_uses_close: 验证非跌停硬止损用收盘价
- test_hard_stop_limitdown_adds_pending: 验证跌停硬止损加入pending_exits
- test_trailing_stop_adds_pending: 验证移动止盈加入pending_exits
- test_t1_blocks_portfolio_stop: 验证T+1阻止组合止损
- test_t1_blocks_drop: 验证T+1阻止drop退出
- test_pending_exits_executed_at_open: 验证pending次日开盘执行

## 文件变更清单
- strategy_v2.py: 删除lines 349-361, 修改lines 430-456
- test_strategy_v2.py: 添加6个新test (lines 457+)
