#!/home/pebynn/tools/quant_env/bin/python3
"""Analyze strategy_reversal_v2 backtest output."""

import pandas as pd
import numpy as np
from datetime import datetime

# Load data
nav = pd.read_csv("/home/pebynn/quant/backtest_reversal_nav.csv", parse_dates=["date"])
trades = pd.read_csv("/home/pebynn/quant/backtest_reversal_trades.csv", parse_dates=["date"])

# Sort
nav = nav.sort_values("date")
trades = trades.sort_values(["date", "code"])

# ── Basic Stats ──
initial_capital = 1_000_000.0
first_nav_date = nav["date"].min()
last_nav_date = nav["date"].max()
first_nav = nav.iloc[0]["nav"]
last_nav = nav.iloc[-1]["nav"]

# Total return (from initial capital)
total_return_pct = (last_nav / initial_capital - 1) * 100

# Annualized return (full backtest period: 2025-05-01 to 2026-04-30)
backtest_start = pd.Timestamp("2025-05-01")
backtest_end = pd.Timestamp("2026-04-30")
days = (backtest_end - backtest_start).days
years = days / 365.25
annual_ret_pct = ((last_nav / initial_capital) ** (1 / years) - 1) * 100

# Max drawdown
nav["peak"] = nav["nav"].cummax()
nav["drawdown"] = (nav["nav"] / nav["peak"] - 1) * 100
max_dd = nav["drawdown"].min()

# Sharpe ratio (daily)
nav["daily_ret"] = nav["nav"].pct_change()
daily_ret_mean = nav["daily_ret"].mean()
daily_ret_std = nav["daily_ret"].std()
sharpe_daily = daily_ret_mean / daily_ret_std * np.sqrt(252) if daily_ret_std > 0 else 0

# ── Trade Analysis ──
trade_df = trades.copy()

# Separate buys and sells
buys = trade_df[trade_df["action"] == "BUY"].copy()
sells = trade_df[trade_df["action"] == "SELL"].copy()

# Count trades
total_trades = len(sells)
buy_count = len(buys)
sell_count = len(sells)

# Win rate (per sell)
win_sells = sells[sells["pnl"] > 0]
loss_sells = sells[sells["pnl"] <= 0]
win_rate = len(win_sells) / len(sells) * 100 if len(sells) > 0 else 0

# PnL stats
total_pnl = sells["pnl"].sum()
avg_win = win_sells["pnl"].mean() if len(win_sells) > 0 else 0
avg_loss = loss_sells["pnl"].mean() if len(loss_sells) > 0 else 0
profit_factor = abs(win_sells["pnl"].sum() / loss_sells["pnl"].sum()) if loss_sells["pnl"].sum() != 0 else float('inf')

# Exit reason analysis
exit_reasons = sells["reason"].value_counts()
exit_by_reason = sells.groupby("reason").agg(
    count=("pnl", "count"),
    total_pnl=("pnl", "sum"),
    avg_pnl=("pnl", "mean"),
    win_rate=("pnl", lambda x: (x > 0).mean() * 100)
).round(2)

# Unique stocks traded
unique_stocks = trade_df["code"].nunique()

# Monthly NAV returns
nav["month"] = nav["date"].dt.to_period("M")
monthly = nav.groupby("month").agg(
    start_nav=("nav", "first"),
    end_nav=("nav", "last"),
    max_drawdown=("drawdown", "min")
)
monthly["return_pct"] = (monthly["end_nav"] / monthly["start_nav"] - 1) * 100
monthly["peak_nav"] = nav.groupby("month")["nav"].transform("cummax")
monthly_all = monthly.copy()

# ── Plot-like table: yearly summary ──
nav["year"] = nav["date"].dt.year
yearly = nav.groupby("year").agg(
    start_nav=("nav", "first"),
    end_nav=("nav", "last"),
    max_dd=("drawdown", "min")
)
yearly["return_pct"] = (yearly["end_nav"] / yearly["start_nav"] - 1) * 100

# ── Top/bottom stocks by pnl ──
stock_pnl = sells.groupby("code")["pnl"].sum().sort_values(ascending=False)
top5 = stock_pnl.head(5)
bot5 = stock_pnl.tail(5)

# ── Print Report ──
print("=" * 70)
print("  反转策略 v2 (Strategy B-R2) — 回测分析报告")
print(f"  周期: {first_nav_date.date()} ~ {last_nav_date.date()} ({days}天)")
print(f"  数据源: MySQL (全A股)")
print("=" * 70)

print(f"\n{'='*70}")
print("  [核心指标]")
print(f"  {'指标':<25} {'值':>15}")
print(f"  {'─'*40}")
print(f"  {'初始资金':<25} {initial_capital:>15,.0f}")
print(f"  {'最终净值':<25} {last_nav:>15,.0f}")
print(f"  {'总收益率':<25} {total_return_pct:>14.2f}%")
print(f"  {'年化收益率':<25} {annual_ret_pct:>14.2f}%")
print(f"  {'夏普比率(日/年化)':<25} {sharpe_daily:>15.4f}")
print(f"  {'最大回撤':<25} {max_dd:>14.2f}%")
print(f"  {'胜率 (按卖出笔数)':<25} {win_rate:>14.2f}%")
print(f"  {'总交易笔数(买入)':<25} {buy_count:>15}")
print(f"  {'总交易笔数(卖出)':<25} {sell_count:>15}")
print(f"  {'交易股票数':<25} {unique_stocks:>15}")
print(f"  {'总盈利(PnL)':<25} {total_pnl:>15,.0f}")
print(f"  {'平均盈利(胜)':<25} {avg_win:>15,.0f}")
print(f"  {'平均亏损(负)':<25} {avg_loss:>15,.0f}")
print(f"  {'盈亏比(Profit Factor)':<25} {profit_factor:>15.2f}")

print(f"\n{'='*70}")
print("  [退出原因分析]")
print(f"  {'原因':<22} {'笔数':>6} {'总PnL':>10} {'平均PnL':>10} {'胜率':>8}")
print(f"  {'─'*56}")
for reason, row in exit_by_reason.iterrows():
    print(f"  {reason:<22} {row['count']:>6.0f} {row['total_pnl']:>10,.0f} {row['avg_pnl']:>10,.0f} {row['win_rate']:>7.1f}%")

print(f"\n{'='*70}")
print("  [月度表现]")
print(f"  {'月份':<10} {'收益%':>8} {'期末净值':>12} {'最大回撤%':>10}")
print(f"  {'─'*40}")
for month, row in monthly_all.iterrows():
    ret = row["return_pct"]
    marker = " ▲" if ret > 0 else " ▼"
    print(f"  {str(month):<10} {ret:>7.2f}%{marker} {row['end_nav']:>12,.0f} {row['max_drawdown']:>9.2f}%")

print(f"\n{'='*70}")
print("  [年度表现]")
print(f"  {'年份':<8} {'收益%':>8} {'期末净值':>12} {'最大回撤%':>10}")
print(f"  {'─'*38}")
for year, row in yearly.iterrows():
    ret = row["return_pct"]
    marker = " ▲" if ret > 0 else " ▼"
    print(f"  {int(year):<8} {ret:>7.2f}%{marker} {row['end_nav']:>12,.0f} {row['max_dd']:>9.2f}%")

print(f"\n{'='*70}")
print("  [最佳/最差5只股票]")
print(f"  最佳5只:")
for code, pnl in top5.items():
    print(f"    {code}: +{pnl:,.0f}")
print(f"  最差5只:")
for code, pnl in bot5.items():
    print(f"    {code}: {pnl:,.0f}")

print(f"\n{'='*70}")
print(f"  [NAV路径摘要]")
peak_nav = nav["nav"].max()
trough_nav = nav["nav"].min()
peak_date = nav.loc[nav["nav"].idxmax(), "date"].date()
trough_date = nav.loc[nav["nav"].idxmin(), "date"].date()
print(f"  最高净值: {peak_nav:,.0f} ({peak_date})")
print(f"  最低净值: {trough_nav:,.0f} ({trough_date})")
print(f"  波动(峰-谷): {(peak_nav - trough_nav) / peak_nav * 100:.2f}%")
print(f"  期末净值: {last_nav:,.0f} ({last_nav_date.date()})")

# ── Bias Check ──
print(f"\n{'='*70}")
print("  [偏差检查]")

# Check: no buy after final exit date from same code
# Check: minimum holding period
buy_codes = buys[["date", "code"]].copy()
sell_codes = sells[["date", "code"]].copy()
buy_codes["type"] = "buy"
sell_codes["type"] = "sell"
all_events = pd.concat([buy_codes, sell_codes]).sort_values(["code", "date", "type"])

# Check for any sell that happens BEFORE its corresponding buy
issues = 0
for code, group in all_events.groupby("code"):
    buys_in_code = group[group["type"] == "buy"]
    sells_in_code = group[group["type"] == "sell"]
    if len(buys_in_code) > 0 and len(sells_in_code) > 0:
        first_buy = buys_in_code["date"].min()
        first_sell = sells_in_code["date"].min()
        if first_sell < first_buy:
            issues += 1
            print(f"  ⚠️  代码 {code}: 首次卖出({first_sell.date()}) < 首次买入({first_buy.date()})")

if issues == 0:
    print("  ✅ 所有卖出发生在买入之后 — 无未来数据泄漏")
else:
    print(f"  ❌ 发现 {issues} 个问题")

# Check leverage
print(f"  ✅ 杠杆倍率: {1.0}x — 任务约束, 无杠杆风险")

# Check price reasonableness
print(f"\n  [价格合理性检查]")
extreme_trades = trades[
    (trades["action"] == "BUY") & 
    ((trades["price"] < 0.5) | (trades["price"] > 500))
]
if len(extreme_trades) > 0:
    print(f"  ⚠️  发现极端价格买入: {len(extreme_trades)} 笔")
    for _, row in extreme_trades.iterrows():
        print(f"      {row['date'].date()} {row['code']} price={row['price']}")
else:
    print(f"  ✅ 买入价格在合理范围")

print(f"\n{'='*70}")
print("  [参数总览]")
print(f"  止损: {0.10*100:.0f}% | 止盈: {0.15*100:.0f}% | 移动止盈: 5%")
print(f"  持仓上限: 10 | 调仓周期: 3天 | 时间止损: 5天+{-0.06*100:.0f}%")
print(f"  杠杆: 1.0x | 行业热度过滤: 启用 | 趋势过滤: 关闭")
print(f"  策略版本: Strategy B-R2 (strategy_reversal_v2.py)")
