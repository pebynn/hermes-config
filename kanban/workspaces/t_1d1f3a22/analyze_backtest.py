import pandas as pd
import numpy as np

df = pd.read_csv('/home/pebynn/quant/backtest_momentum.csv')
df['is_win'] = df['pnl_pct'] > 0

print('=== 回测指标摘要 ===')
print(f'总交易: {len(df)}')
print(f'胜率: {df.is_win.sum()/len(df)*100:.1f}%')
print(f'平均盈亏: {df.pnl_pct.mean():.2f}%')
print(f'平均盈利: {df[df.is_win].pnl_pct.mean():.2f}%')
print(f'平均亏损: {df[~df.is_win].pnl_pct.mean():.2f}%')
print(f'总收益率(未加权): {df.pnl_pct.sum():.2f}%')
print(f'单笔最大盈利: {df.pnl_pct.max():.2f}%')
print(f'单笔最大亏损: {df.pnl_pct.min():.2f}%')
print()

# 净值模拟 (每笔权重 = 1/TOP_N = 1/5 = 20%)
nav = 1.0
navs = [1.0]
for pnl in df.pnl_pct.values:
    nav *= (1 + pnl/100 * 0.2)
    navs.append(nav)

annual_return = (nav ** (252/77) - 1) * 100
dd = pd.Series(navs)
running_max = dd.expanding().max()
drawdown = (dd - running_max) / running_max
max_dd = drawdown.min() * 100

daily_returns = np.diff(navs)
sharpe = np.sqrt(252) * np.mean(daily_returns) / np.std(daily_returns) if np.std(daily_returns) > 0 else 0

print('=== 净值分析 (权重20%/笔, 252日年化) ===')
print(f'终值NAV: {nav:.4f}')
print(f'年化收益: {annual_return:.2f}%')
print(f'夏普比率: {sharpe:.2f}')
print(f'最大回撤: {max_dd:.2f}%')
print(f'日收益率均值: {np.mean(daily_returns)*100:.3f}%')
print(f'日收益率标准差: {np.std(daily_returns)*100:.3f}%')
print(f'交易天数: 77')
print()

# 按月分析
df['month'] = pd.to_datetime(df['entry_date']).dt.month
monthly = df.groupby('month').agg(
    trades=('pnl_pct', 'count'),
    win_rate=('is_win', 'mean'),
    avg_pnl=('pnl_pct', 'mean'),
    total_pnl=('pnl_pct', 'sum')
)
print('=== 月度分析 ===')
for m, row in monthly.iterrows():
    print(f'  {int(m)}月: {int(row.trades)}笔 胜率{row.win_rate*100:.1f}% 平均{row.avg_pnl:.2f}% 总和{row.total_pnl:.2f}%')

# 退出原因分析
print()
print('=== 退出原因分布 ===')
for reason, grp in df.groupby('exit_reason'):
    print(f'  {reason}: {len(grp)}笔 胜率{grp.is_win.mean()*100:.1f}% 均盈亏{grp.pnl_pct.mean():.2f}%')
