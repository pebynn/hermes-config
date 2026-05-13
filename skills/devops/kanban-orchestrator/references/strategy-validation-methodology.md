# 策略验证标准方法论

全周期回测 + 逐年分解 + OOS + 参数扫描四步验证法。

## Step 1: 全周期主回测

```bash
BT_START=2021-01-01 BT_END=2025-12-31 python3 strategy.py
```
输出：`output_v2/full_period_results.json` + `full_period_nav.csv` + `full_period_trades.csv`

关键指标：年化/夏普/回撤/胜率/交易数/退出原因分布。

## Step 2: 逐年分解

对每个年份单独跑，暴露策略在不同市场环境下的表现：

```bash
for y in 2021 2022 2023 2024 2025; do
  BT_START=$y-01-01 BT_END=$y-12-31 python3 strategy.py
  cp results.json output_v2/yr_${y}_results.json
done
```

关注：熊市年(2022)表现 / 震荡年(2023-2024)表现 / 牛年(2021,2025)是否有选股Alpha还是纯Beta。

## Step 3: 样本外验证(OOS)

```bash
BT_START=2026-01-01 BT_END=$(date +%Y-%m-%d) python3 strategy.py
cp results.json output_v2/oos_2026_results.json
```

判断标准：
- OOS年化不低于全期年化的50% → 策略稳健
- OOS年化远超全期如1209% vs 89% → 警惕：短样本偏误或过拟合
- OOS回撤显著低于全期 → 可能当前市场恰好有利，非策略鲁棒

## Step 4: 参数敏感性扫描

```bash
for T in 0.5 1.0 1.5 2.0 3.0 4.0; do
  BT_START=2021-01-01 BT_END=2025-12-31 python3 strategy.py --param $T
  cp results.json output_v2/sweep/results_${T}.json
done
```

目标：确认最优参数附近结果稳定，非尖锐峰(过拟合信号)。

## 输出汇总

最终应有一张完整表：

| 周期 | 年化% | 夏普 | 回撤% | 胜率% | 交易数 |
|:--|--:|--:|--:|--:|--:|
| 2021-2025全期 |  |  |  |  |  |
| 2026 OOS |  |  |  |  |  |
| 2021年 |  |  |  |  |  |
| ...逐年... |  |  |  |  |  |

## 文件命名约定

在 `output_v2/` 下：
- `full_period_*` — 全周期主回测
- `oos_2026_*` — 样本外
- `yr_20XX_*` — 逐年
- `ps10_* / ps15_*` — 参数调整对比
- `ic_sweep/results_T*.json` — 参数扫描

## 🔴 并发瓶颈

**MySQL kline表单表瓶颈**：多个strategy_v2进程同时启动时全部卡在 `load_data_v2()` 阶段——每个进程都执行 `SELECT * FROM kline WHERE trade_date>=start AND trade_date<=end ORDER BY code,trade_date`，同时读全市场K线导致I/O争抢。

现象：进程CPU时间极小(0:02)但已跑5+分钟，输出为空。

缓解：
1. 串行化数据加载阶段 — 逐个启动回测，上一轮进模拟阶段再启下一个
2. 或用看板逐个排队（依赖链 gating）
3. 预热窗WARMUP_DAYS=120意味着2026回测也要读~8个月全市场数据，不能因为交易日少就认为快
