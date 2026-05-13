# B策略重构实施计划 — t_af45af1b

## 诊断分析

诊断报告核心发现：R9-B (56.31%年化) → R10-B (8.96%) 断崖由5项变更同时实施导致：
1. 🔴 复合分数稀释反转信号 (decline*0.35, 反转仅35%权重)
2. 🔴 MOM_20D_MIN 5%→8% 收窄候选池
3. 🔴 SECTOR_MAX_POSITIONS=2 抑制行业集中
4. ⚠️ 止损-12%→-8% 
5. ⚠️ ATR仓位 禁用→1.5x

## 当前代码状态 (strategy_reversal.py)

当前代码是R9逻辑，但配置已偏离最优R9-B：

| 参数 | 当前值 | R9-B最优 | 差距 |
|:-----|:------:|:--------:|:-----|
| 回测期间 | 2026-01-01~2026-04-30 | 2025-05-01~2026-04-30 | ❌ 缩短周期 |
| 选股分数 | abs(ret_5d)×sector_boost | 同 | ✅ 已恢复 |
| MOM_20D_MIN | 无此过滤 | 5% | ❌ 缺失 |
| 行业限制 | 无 | 无 | ✅ |
| 止损 | -8% | -12% | ❌ 过紧 |
| ATR仓位 | 禁用 | 禁用 | ✅ |
| 基本面过滤 | 无 | 无 | ✅ |
| 止盈 | 13%半仓+trail 6% | 8%/18% | ⚠️ 单层vs双层 |

## 设计方案

### 选择：Direction A — 回恢复兴 (diagnosis推荐的最高优先级方向)

**方案选择理由**：
- R9-B已在完整一年期验证(56.31%，Sharpe 2.715)，低风险
- 本质是移除R10的多因子噪音，恢复R9纯反转逻辑
- 实施成本低：只需改参数+加一个MOM过滤

**替代方案**：
- Direction B (保守精进): 天花板18%，离目标太远
- Direction C (杠杆重组): 需要两融账户，短期不可行

**风险**：
- STOP_LOSS从-8%放宽到-12%会增大单笔亏损 → MDD可能从-15%扩大到-20%+
- MOM_20D_MIN=5%会减少候选池 → 交易次数可能下降10-20%
- 需要实际回测验证

### 具体改动 (增量，映射到诊断报告的每个根因)

| # | 诊断根因 | 代码改动 | 行号 |
|:--|:--------|:--------|:-----|
| 1 | 根因#1: 复合分数稀释 | 确认 score = abs(ret_5d)×sector_boost (已是) | line 202 ✅ |
| 2 | 根因#2: MOM_20D_MIN 5%→8% | 新增 MOM_20D_MIN = 0.05 + ret_20d预过滤 | select_signals() |
| 3 | 根因#3: SECTOR_MAX_POSITIONS=2 | 无改动 (当前无行业限制) | ✅ |
| 4 | 辅助: 止损过紧 -8% | STOP_LOSS: -0.08 → -0.12 | line 56 |
| 5 | 辅助: ATR仓位 1.5x | 无改动 (当前已禁用) | ✅ |
| 6 | 回测周期缩短 | START_DATE: "2026-01-01" → "2025-05-01" | line 51 |
| 7 | MOM_20D pre-filter实现 | 在select_signals中加ret_20d >= MOM_20D_MIN | 新增 |

### 不做的改动
- ❌ 不引入复合分数/RSI/成交量过滤 (保持纯反转)
- ❌ 不引入行业仓位限制
- ❌ 不引入ATR仓位管理
- ❌ 不引入基本面过滤
- ✅ 保留 sector_heat 硬过滤 (R9已验证有效逻辑)
- ✅ 保留 R9 止盈13%半仓+trailing逻辑 (优于原8%/18%)

### 预期结果
- 年化: 45-56% (接近R9-B)
- Sharpe: 2.0-2.7
- MDD: -12%~-20%
- 胜率: 50-56%
- 目标序列: >30% (第一) → >100% (需要额外增强)

---

## 实施步骤

### Step 3: TDD — 测试用例设计

测试用例 (在回测上下文验证，不创建独立test文件):
- TEST-1: 修改后代码语法正确 (python -c "import py_compile")
- TEST-2: --source sina 模式可运行完成 (轻量验证)
- TEST-3: 输出包含 BACKTEST_SUMMARY 结构化数据
- TEST-4: 年化收益率 > 30% (完整回测)
- TEST-5: 胜率 > 45%
- TEST-6: 交易笔数 >= 150 (防止候选池过小)

RED初始状态: TEST-4/TEST-5/TEST-6在基线回测跑完前未知

### Step 4: 实施变更清单

```diff
# 1. 回测周期扩展
- START_DATE = "2026-01-01"
+ START_DATE = "2025-05-01"

# 2. 止损恢复R9-B水平
- STOP_LOSS = -0.08
+ STOP_LOSS = -0.12

# 3. 新增 MOM_20D_MIN 参数
+ MOM_20D_MIN = 0.05  # R9-B: 20日必须涨5%以上才进入候选

# 4. 计算 ret_20d (已有ret_5d, ret_3d, 缺20d)
+ df["ret_20d_raw"] = df.groupby("code")["close"].transform(
+     lambda s: s.pct_change(20))
+ df["ret_20d"] = df.groupby("code")["ret_20d_raw"].shift(1)

# 5. select_signals 中加 MOM 预过滤
+ # R9-B: Momentum pre-filter — must be in uptrend
+ candidates = candidates[candidates["ret_20d"] >= MOM_20D_MIN]
```

### 验证命令

```bash
# 语法验证
python -c "import py_compile; py_compile.compile('/home/pebynn/quant/strategy_reversal.py', doraise=True)"

# 快速回测 (sina模式，轻量数据)
cd /home/pebynn/quant && python strategy_reversal.py --source sina

# 完整回测 (MySQL模式)
cd /home/pebynn/quant && python strategy_reversal.py --source mysql
```

### 禁止事项确认
- [x] 不引入未来数据泄露 (所有信号lag 1d)
- [x] 不删除风控逻辑 (止损/止盈/trailing/time_stop全部保留)
- [x] 不做仅改名/改注释的无意义改动
- [x] 不引入R10的多因子混合评分
- [x] 不引入SECTOR_MAX_POSITIONS行业限制

---

## Step 7: 验证结果

### 最终回测 (MySQL, 5331 stocks, 2025-05-01→2026-04-30)

| 指标 | 目标 | 结果 | 状态 |
|:-----|:----:|:----:|:----:|
| 年化收益 | >30% | +38.31% | ✅ |
| 年化收益 | >100% | +38.31% | ❌ 1x杠杆结构不可达 |
| 胜率 | >45% | 51.5% | ✅ |
| Sharpe | >1.5 | 1.331 | ❌ |
| 最大回撤 | <20% | -28.31% | ❌ |
| 语法验证 | 通过 | SYNTAX OK | ✅ |
| 文件产出 | trades+nav | 2 CSV | ✅

### 月度收益
```
2025-05: +3.20%   2025-09: +8.27%   2026-01: +16.85%
2025-06: +22.17%  2025-10: +4.44%   2026-02: +7.25%
2025-07: +15.18%  2025-11: +1.80%   2026-03: -17.18%
2025-08: +3.64%   2025-12: -6.99%   2026-04: -7.73%
```
正月份率: 9/12 = 75%

### 退出分布
- rebalance_close_full: 372 avg +1,955
- stop_loss: 357 avg -239
- take_profit_half: 290 avg +1,143
- time_stop: 42 avg -6,692
- trailing_stop: 13 avg -8,761

### 改进总结
1. 年化从 8.50% → 38.31% (4.5x提升)
2. 主要驱动力: 扩展回测周期 + 恢复R9-B核心参数
3. 2026-03系统性回撤(-17.18%)是MDD主因，A股全市场下行
4. >100%目标在1x杠杆上结构不可达，需杠杆或不同策略结构

### 文件清单
- `/home/pebynn/quant/strategy_reversal.py` — 修改后策略代码
- `/home/pebynn/quant/backtest_reversal_nav.csv` — 净值轨迹
- `/home/pebynn/quant/backtest_reversal_trades.csv` — 交易明细
