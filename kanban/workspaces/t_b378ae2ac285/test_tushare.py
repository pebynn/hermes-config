#!/home/pebynn/tools/quant_env/bin/python3
"""Quick test: run tushare daily fetch only (no disk writes) to measure API speed."""
import sys, time
sys.path.insert(0, '/home/pebynn/quant')

import pandas as pd
from datetime import datetime

today_fmt = datetime.now().strftime('%Y%m%d')
print(f'Testing tushare bulk API for date: {today_fmt}', flush=True)

t0 = time.time()
from daily_kline_update import fetch_all_tushare
df, msg = fetch_all_tushare(today_fmt)
elapsed = time.time() - t0

print(f'tushare bulk API: {msg}')
if df is not None:
    print(f'  Rows: {len(df)}')
    print(f'  Columns: {list(df.columns)}')
    print(f'  Sample codes: {df["code"].head(3).tolist()}')
print(f'  Elapsed: {elapsed:.1f}s')
print(f'  Total: {elapsed:.1f}s')
