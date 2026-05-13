#!/home/pebynn/tools/quant_env/bin/python3
"""Test chan_buy_signal with MySQL data (full history)."""
import sys
sys.path.insert(0, '/home/pebynn/quant')
import pandas as pd
from pathlib import Path
from data_common import kline_from_db, _get_db_engine
from chan_buy_signal import detect_chan_buy2

# Check MySQL data volume
engine = _get_db_engine()
cnt = pd.read_sql("SELECT code, COUNT(*) as cnt FROM kline GROUP BY code ORDER BY cnt DESC LIMIT 10", engine)
print("Top 10 stocks by row count:")
for _, row in cnt.iterrows():
    print(f"  {row['code']}: {row['cnt']} rows")

# Test a few with MySQL data
from datetime import datetime, timedelta
codes = ['000001', '600000', '300750', '000858', '002415', '601318']
for code in codes:
    db_df = kline_from_db(code=code, start_date="2024-01-01")
    if db_df is None or len(db_df) < 60:
        print(f'{code}: MySQL only {len(db_df) if db_df is not None else 0} rows — skip')
        continue
    n = len(db_df)
    # Rename columns to match expected format
    col_map = {
        "trade_date": "日期", "open": "开盘", "close": "收盘",
        "high": "最高", "low": "最低", "volume": "成交量",
        "amount": "成交额", "amplitude": "振幅",
        "pct_chg": "涨跌幅", "change": "涨跌额", "turnover": "换手率",
    }
    df = db_df.rename(columns=col_map)
    buy2 = detect_chan_buy2(df)
    if buy2 is not None and not buy2.empty:
        print(f'{code} ({n} rows): {len(buy2)} buy2 signals')
        print(f'  Latest: {buy2.iloc[-1].to_dict()}')
    else:
        print(f'{code} ({n} rows): no buy2 signals')
