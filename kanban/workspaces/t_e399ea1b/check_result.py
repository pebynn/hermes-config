import pandas as pd, numpy as np

df = pd.read_csv('/home/pebynn/quant/backtest_momentum.csv')
print(f"Total trades: {len(df)}")
print(f"Win rate: {(df['pnl_pct']>0).mean()*100:.1f}%")
print(f"Avg PnL: {df['pnl_pct'].mean():.2f}%")
print(f"Max win: {df['pnl_pct'].max():.2f}%")
print(f"Max loss: {df['pnl_pct'].min():.2f}%")
print(f"\nExit reason breakdown:")
print(df['exit_reason'].value_counts().to_string())
print(f"\nStop loss count: {(df['exit_reason']=='hard_stop').sum()} / {(df['exit_reason']=='trailing_profit').sum()} trailing")
print(f"\nDate range: {df['entry_date'].min()} to {df['exit_date'].max()}")
print(f"\nFirst 10 trades:")
print(df.head(10).to_string())
