import pandas as pd
import numpy as np

df = pd.read_parquet('/home/pebynn/quant/cache/sina_kline_2025_2026.parquet')
df = df.rename(columns={'date': 'trade_date'})
df = df[(df['trade_date'] >= '2025-12-15') & (df['trade_date'] <= '2026-04-30')]

print(f'Total rows: {len(df)}')
print(f'Unique stocks: {df["code"].nunique()}')
print()

stock_days = df.groupby('code').size()
stocks_with_60 = stock_days[stock_days >= 60]
print(f'Stocks with >=60d data: {len(stocks_with_60)}')

count = 0
for code in stocks_with_60.index:
    s = df[df['code'] == code].sort_values('trade_date')
    last = s.iloc[-1]
    close_series = s['close'].values
    ma60 = np.mean(close_series[-60:])
    vol_ma20 = np.mean(s['volume'].values[-20:])
    vol_ratio = last['volume'] / vol_ma20 if vol_ma20 > 0 else 0
    
    if last['close'] > ma60 and vol_ratio > 2.0:
        print(f'{code}: close={last["close"]:.2f} ma60={ma60:.2f} vol_ratio={vol_ratio:.2f} last_date={last["trade_date"]} rows={len(s)}')
        count += 1

print(f'\nStocks meeting above_ma60 + vol_ratio>2.0: {count}')
