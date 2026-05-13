import pandas as pd

df = pd.read_parquet('/home/pebynn/quant/cache/sina_kline_2025_2026.parquet')
unique_codes = df['code'].nunique()
print(f"Sina parquet: {len(df)} rows, {unique_codes} unique stocks")
print(f"Date range: {df['date'].min()} -> {df['date'].max()}")
