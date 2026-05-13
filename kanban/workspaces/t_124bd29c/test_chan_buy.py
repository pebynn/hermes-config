#!/home/pebynn/tools/quant_env/bin/python3
"""Test chan_buy_signal module with a few stocks."""
import sys
sys.path.insert(0, '/home/pebynn/quant')
import pandas as pd
from pathlib import Path
from chan_buy_signal import detect_chan_buy2

kdir = Path.home() / '.finquant' / 'cache' / 'kline'
codes = ['000001', '600000', '300750', '000858', '002415']
for code in codes:
    path = kdir / f'{code}.parquet'
    if not path.exists():
        print(f'{code}: no parquet')
        continue
    kline = pd.read_parquet(path)
    n = len(kline)
    buy2 = detect_chan_buy2(kline)
    if buy2 is not None and not buy2.empty:
        print(f'{code} ({n} rows): {len(buy2)} buy2 signals')
        print(f'  Latest: {buy2.iloc[-1].to_dict()}')
    else:
        print(f'{code} ({n} rows): no buy2 signals')
