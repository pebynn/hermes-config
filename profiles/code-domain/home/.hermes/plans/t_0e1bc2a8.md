# R2-C 代码优化计划

## 元信息
- Task: t_0e1bc2a8
- 策略: C (缠论二买 + 量价趋势)
- 文件: /home/pebynn/quant/evo_optimizer/strategy_chan.py
- R1基线: 年化96.28%, 夏普0.67, 胜率43.1%, MDD-25.24%, 339笔
- 差距: 距300%目标差203.72%

## 设计方案

### 方案选择: 四参数激进修改 + 结构安全网

R1的核心矛盾：过于保守的退出机制扼杀了收益。
- 44%的仓位被时间强制退出（max_hold），平均仅+3.62%
- 30%被止损退出，但实际平均亏损-10.28%（跳空缺口导致超过-8%止损线）
- 只有25%达到止盈目标

**R2策略**: 放宽exit约束，缩紧entry质量 → 让赢家奔跑，排除弱信号。

### 具体参数变更

| 参数 | R1值 | R2值 | 理由 |
|------|------|------|------|
| STOP_LOSS | -0.08 | -0.10 | 减少止损触发，给价格恢复空间。R1止损实际均值已达-10.28%，放宽到-10%不会显著恶化单笔亏损 |
| MAX_HOLD_DAYS | 30 | 120 | 核心改动。消除44%仓位被时间退出的问题。120天≈6个月，在1年回测中几乎等同于无限制，但防止僵尸仓位 |
| MAX_HOLDINGS | 10 | 12 | 更分散化，利用量比>3.0筛选后的高质量信号 |
| MIN_HOLDINGS | 8 | 10 | 提高组合集中度门槛 |
| VOL_RATIO_MIN | 2.0 | 3.0 | 仅进入高量比信号，提高单笔质量 |

### 替代方案（已排除）

1. **仅放宽止损不改持仓限制**: R1的max_hold是最大拖累，不改它R2效果有限
2. **同时提高止盈到+15%**: 可能进一步加剧"无法止盈"的问题，10%在30天窗口内可达性较好
3. **VOL_RATIO_MIN放宽到4.0**: 与MIN_HOLDINGS=10冲突严重，可能导致大量调仓日无候选
4. **添加trailing stop**: 结构改动太大，超出了简单参数优化的范围，留到R3

### 风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 信号稀疏 (VR>3.0 + MIN=10) | 中 | 交易数<150，统计不显著 | 若交易数<200，R3回退VR到2.5 |
| 止损-10%单笔亏损扩大 | 低 | 个别股票-12%+ | 120天窗口给足够恢复时间 |
| 持仓周期过长 | 中 | 资本效率降低 | 120天安全网+每次调仓重新评估 |
| NAV计算漂移 | 低 | 长持仓导致NAV累积误差 | 使用contribution-based NAV，已验证正确 |

### 铁律检查清单
- [x] LEVERAGE=1.0 (不可改)
- [x] 无未来函数 (shift(1) + open[i+1] 保持不变)
- [x] OUTPUT_FILE = /home/pebynn/quant/evo_optimizer/backtest_C.csv
- [x] 数据: fallback_resolver.load_kline()

## 代码改动详情

### 改动1: docstring 更新 (行3-31)
```
-R1-C: 未来函数修复 + 参数优化
+R2-C: 激进退出优化 + 入场质量提升
```

### 改动2: 参数常量 (行56-60)
```python
STOP_LOSS  = -0.10  # R2: widened from -0.08
MAX_HOLD_DAYS = 120  # R2: effectively unlimited (from 30)
MAX_HOLDINGS = 12    # R2: increased from 10
MIN_HOLDINGS = 10    # R2: increased from 8
VOL_RATIO_MIN = 3.0  # R2: tightened from 2.0
```

### 改动3: main() 打印信息 (行196-199)
更新显示的参数值以匹配R2

### 不改动的关键行 (铁律验证)
- 行51: LEVERAGE = 1.0 (不碰)
- 行151: vol_ma20 = ... .shift(1) (未来函数已修复，不碰)
- 行407-413: entry at open[i+1] (未来函数已修复，不碰)
- 行61: OUTPUT_FILE (不变)

## TDD计划

### 测试用例

**测试1: test_iron_rules.py** — 验证铁律未破
```python
import ast, sys
sys.path.insert(0, '/home/pebynn/quant/evo_optimizer')

# 1. LEVERAGE=1.0
# 2. VOL_RATIO_MIN=3.0 (R2值)
# 3. STOP_LOSS=-0.10 (R2值)
# 4. MAX_HOLD_DAYS=120 (R2值)
# 5. OUTPUT_FILE 指向 backtest_C.csv
# 6. vol_ma20 使用 .shift(1)
# 7. 无未来函数: open[i+1] 在entry逻辑中
```

**测试2: test_syntax** — python3 -m py_compile

**测试3: test_no_future_leak** — 验证关键行:
- line with `vol_ma20` contains `.shift(1)`
- entry logic references `next_i = i + 1` and `open[next_i]`

## 实施步骤

1. ✅ 读取完整代码 (已完成)
2. 修改5个参数常量 (行56-60)
3. 更新docstring头部注释 (行3-13)
4. 更新main()打印信息 (行196-199)
5. TDD: 写测试并验证 (至少1个RED → 修改后GREEN)
6. python3 -m py_compile 语法检查
7. 自审code-review (6步流程)
8. 确认所有铁律
9. 实际运行回测验证 (可选 — 耗时)

## 预期结果

乐观预期: 年化180-250%, 交易200-280笔, 胜率45-50%
保守预期: 年化130-180%, 交易150-200笔, 胜率42-47%
关键驱动: 放宽max_hold让更多仓位有机会达到+10%止盈，VOL_RATIO_MIN=3.0提高单笔质量。
