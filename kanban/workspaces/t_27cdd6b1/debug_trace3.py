"""Check when buy2 signals are firing and their active window coverage."""
import sys, os
sys.path.insert(0, '/home/pebynn/quant')
import pandas as pd
import numpy as np
from datetime import timedelta

from strategy_chan import precompute_indicators, detect_buy2_dates

SINA_PARQUET_PATH = '/home/pebynn/quant/cache/sina_kline_2025_2026.parquet'
START_DATE = "2026-01-01"
END_DATE = "2026-04-30"
WARMUP_DAYS = 200
BUY2_ACTIVE_DAYS = 12

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

# Find all buy2 dates across all stocks
all_buy2_dates = set()
for code, df in code_klines.items():
    dates_arr = df["日期"].values
    close_v = df["收盘"].values.astype(np.float64)
    high_v = df["最高"].values.astype(np.float64)
    low_v = df["最低"].values.astype(np.float64)
    vol_v = df["成交量"].values.astype(np.float64)
    n = len(df)
    ind = precompute_indicators(close_v, high_v, low_v, vol_v, n)
    buy2_set = detect_buy2_dates(close_v, high_v, low_v, vol_v, dates_arr, ind)
    for d in buy2_set:
        all_buy2_dates.add(d)

sorted_dates = sorted(all_buy2_dates, key=lambda x: pd.Timestamp(x))
print(f"Total unique buy2 signal dates: {len(sorted_dates)}")
for d in sorted_dates:
    print(f"  {d}")

# Now check: for each buy2 date, what's the active window (signal day + 11 calendar days)
print()
print("--- Active windows ---")
rebalance_dates_full = pd.date_range(start="2026-01-01", end="2026-04-30", freq="7D")
print(f"Rebalance dates: {[str(d.date()) for d in rebalance_dates_full]}")

print()
print("Buy2 signal -> active window (12d) overlap with rebalance windows:")
for d in sorted_dates:
    dt = pd.Timestamp(d)
    active_end = dt + timedelta(days=BUY2_ACTIVE_DAYS - 1)
    print(f"  {d} -> active to {active_end.date()}", end="")
    
    # Check each rebalance window [rd-5, rd+2]
    overlaps = []
    for rd in rebalance_dates_full:
        w_start = rd - timedelta(days=5)
        w_end = rd + timedelta(days=2)
        if dt <= w_end and active_end >= w_start:
            overlaps.append(str(rd.date()))
    if overlaps:
        print(f" overlaps with rebalances: {overlaps}")
    else:
        print(" NO overlap with any rebalance window")
