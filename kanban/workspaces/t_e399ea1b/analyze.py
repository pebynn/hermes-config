import pandas as pd, numpy as np

df = pd.read_csv('/home/pebynn/quant/backtest_momentum.csv')

# Detailed breakdown by exit reason
print("=== BY EXIT REASON ===")
for reason in df['exit_reason'].unique():
    sub = df[df['exit_reason']==reason]
    print(f"\n{reason} ({len(sub)} trades):")
    print(f"  Win rate: {(sub['pnl_pct']>0).mean()*100:.1f}%")
    print(f"  Mean PnL: {sub['pnl_pct'].mean():.2f}%")
    print(f"  Median PnL: {sub['pnl_pct'].median():.2f}%")
    print(f"  Sum PnL: {sub['pnl_pct'].sum():.2f}%")
    print(f"  Avg holding days: {(pd.to_datetime(sub['exit_date']) - pd.to_datetime(sub['entry_date'])).dt.days.mean():.1f}")

# Monthly analysis
print("\n=== MONTHLY ===")
df['exit_date'] = pd.to_datetime(df['exit_date'])
df['month'] = df['exit_date'].dt.to_period('M')
monthly = df.groupby('month').agg(
    trades=('pnl_pct','count'),
    win_rate=('pnl_pct', lambda x: (x>0).mean()*100),
    avg_pnl=('pnl_pct','mean'),
    sum_pnl=('pnl_pct','sum')
)
print(monthly.to_string())

# PnL distribution
print("\n=== PnL DISTRIBUTION ===")
bins = [-100, -8, -5, -2, 0, 2, 5, 10, 20, 50, 100]
labels = ['<-8%','-8~-5%','-5~-2%','-2~0%','0~2%','2~5%','5~10%','10~20%','20~50%','>50%']
df['pnl_bin'] = pd.cut(df['pnl_pct'], bins=bins, labels=labels)
print(df['pnl_bin'].value_counts().sort_index().to_string())

# PnL components
print(f"\n=== PnL COMPONENTS ===")
print(f"Total sum PnL%: {df['pnl_pct'].sum():.2f}%")
print(f"Winning trades sum: {df[df['pnl_pct']>0]['pnl_pct'].sum():.2f}%")
print(f"Losing trades sum: {df[df['pnl_pct']<0]['pnl_pct'].sum():.2f}%")
print(f"Avg win: {df[df['pnl_pct']>0]['pnl_pct'].mean():.2f}%")
print(f"Avg loss: {df[df['pnl_pct']<0]['pnl_pct'].mean():.2f}%")

# Check HARD_STOP at exactly -8% clustering
hard_stop_pnls = df[df['exit_reason']=='hard_stop']['pnl_pct']
print(f"\n=== HARD STOP ANALYSIS ===")
print(f"Count at exactly -8.00: {(hard_stop_pnls == -8.0).sum()} / {len(hard_stop_pnls)}")
print(f"Hard stop PnL range: {hard_stop_pnls.min():.2f}% to {hard_stop_pnls.max():.2f}%")

# Also look at entry timing patterns
df['entry_dayofweek'] = pd.to_datetime(df['entry_date']).dt.dayofweek
print(f"\n=== ENTRY DAY OF WEEK ===")
print(df.groupby('entry_dayofweek')['pnl_pct'].agg(['count','mean']).to_string())
