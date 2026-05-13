import pandas as pd

df = pd.read_parquet('/home/pebynn/quant/cache/sina_kline_2025_2026.parquet')
print('Shape:', df.shape)
print('Columns:', df.columns.tolist())
print('Dtypes:')
print(df.dtypes)
print()
print('First 2 rows:')
print(df.head(2).to_string())
print()
date_cols = [c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()]
print('Date-like columns:', date_cols)
