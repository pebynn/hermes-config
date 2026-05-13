import pandas as pd

df = pd.read_parquet('/home/pebynn/quant/cache/sina_kline_2025_2026.parquet')
# Count rows per stock
per_stock = df.groupby('code').size()
print(f"Min rows per stock: {per_stock.min()}")
print(f"Max rows per stock: {per_stock.max()}")
print(f"Mean rows per stock: {per_stock.mean():.1f}")
print(f"Stocks with >= 80 rows: {(per_stock >= 80).sum()}")
print(f"Stocks with >= 60 rows: {(per_stock >= 60).sum()}")
print(f"Stocks with >= 40 rows: {(per_stock >= 40).sum()}")
print()
# Check unique dates
dates = sorted(df['date'].unique())
print(f"Total trading days: {len(dates)}")
print(f"Date range: {dates[0]} -> {dates[-1]}")
print(f"First 5 dates: {dates[:5]}")
print(f"Last 5 dates: {dates[-5:]}")
