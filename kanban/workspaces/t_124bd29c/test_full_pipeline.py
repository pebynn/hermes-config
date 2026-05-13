#!/home/pebynn/tools/quant_env/bin/python3
"""Test full pipeline: MySQL → kline_from_db → detect_chan_buy2"""
import sys
sys.path.insert(0, '/home/pebynn/quant')
import pandas as pd
from data_common import kline_from_db
from chan_buy_signal import detect_chan_buy2

codes = ['000001', '600000', '300750', '000858', '601318', '002415', '000333', '600519']
for code in codes:
    db_df = kline_from_db(code=code, start_date="2024-07-01")
    if db_df is None or len(db_df) < 60:
        print(f'{code}: only {len(db_df) if db_df is not None else 0} rows — skip')
        continue
    n = len(db_df)
    buy2 = detect_chan_buy2(db_df)  # already has 日期 column from the rename
    if buy2 is not None and not buy2.empty:
        print(f'{code} ({n} rows): {len(buy2)} buy2 signals')
        print(f'  Latest: date={buy2.iloc[-1]["date"]}, price={buy2.iloc[-1]["price"]:.2f}, '
              f'atr={buy2.iloc[-1]["atr"]:.2f}, vol_ratio={buy2.iloc[-1]["vol_ratio"]:.3f}, '
              f'pullback={buy2.iloc[-1]["pullback"]:.2f}')
    else:
        print(f'{code} ({n} rows): no buy2 signals')
