"""Debug: trace rebalance candidate selection for Sina backtest."""
import sys, os
sys.path.insert(0, '/home/pebynn/quant')
import pandas as pd
import numpy as np
from datetime import timedelta

# Load and prepare data (same as main())
SINA_PARQUET_PATH = '/home/pebynn/quant/cache/sina_kline_2025_2026.parquet'
START_DATE = "2026-01-01"
END_DATE = "2026-04-30"
WARMUP_DAYS = 200
BUY2_ACTIVE_DAYS = 12
VOL_RATIO_MIN = 2.0
REBALANCE_INTERVAL = 7
MAX_HOLDINGS = 8
MIN_HOLDINGS = 6

all_k = pd.read_parquet(SINA_PARQUET_PATH)
all_k = all_k.rename(columns={"date": "trade_date"})
all_k["trade_date"] = all_k["trade_date"].astype(str)

data_start = (pd.Timestamp(START_DATE) - timedelta(days=WARMUP_DAYS)).strftime("%Y-%m-%d")
all_k = all_k[(all_k["trade_date"] >= data_start) & (all_k["trade_date"] <= END_DATE)]

all_k = all_k.rename(columns={
    "trade_date": "日期", "open": "开盘", "close": "收盘",
    "high": "最高", "low": "最低", "volume": "成交量", "amount": "成交额",
})
all_k["日期"] = all_k["日期"].astype(str)

code_klines = {}
for code, grp in all_k.groupby("code"):
    grp = grp.sort_values("日期").reset_index(drop=True)
    if len(grp) >= 60:
        code_klines[code] = grp

all_dates = sorted(set(d for code in code_klines for d in code_klines[code]["日期"].values), key=lambda x: pd.Timestamp(x))
backtest_dates = [d for d in all_dates if START_DATE <= d <= END_DATE]
rebalance_dates = backtest_dates[::REBALANCE_INTERVAL]

print(f"Total stocks: {len(code_klines)}")
print(f"Backtest dates: {len(backtest_dates)} ({backtest_dates[0]} to {backtest_dates[-1]})")
print(f"Rebalance dates: {len(rebalance_dates)}")
print()

# For each rebalance date, count stocks with active buy2 signals in the window
for rd_idx, rd in enumerate(rebalance_dates):
    rd_dt = pd.Timestamp(rd)
    start_dt = rd_dt - timedelta(days=5)
    end_dt = rd_dt + timedelta(days=2)
    
    # Count stocks with data on this date
    stocks_with_data = 0
    buy2_active_count = 0
    vol_ok_count = 0
    
    for code, df in code_klines.items():
        d2i = {str(d): i for i, d in enumerate(df["日期"].values)}
        close_v = df["收盘"].values.astype(np.float64)
        
        # Check if stock has data near rebalance date
        for check_date in backtest_dates:
            check_dt = pd.Timestamp(check_date)
            if start_dt <= check_dt <= end_dt:
                if check_date in d2i:
                    stocks_with_data += 1
                    break
    
    print(f"Rebalance {rd_idx+1}: {rd} | window=[{start_dt.date()}, {end_dt.date()}] | "
          f"stocks_in_window={stocks_with_data}")
    if rd_idx >= 4:
        print("  (stopping early for brevity)")
        break
