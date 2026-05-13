"""Check ACTUAL rebalance dates from the script (trading day based) vs buy2."""
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

# Compute backtest_dates and rebalance_dates EXACTLY like the script
all_dates = sorted(set(d for code in code_klines for d in code_klines[code]["日期"].values), key=lambda x: pd.Timestamp(x))
backtest_dates = [d for d in all_dates if START_DATE <= d <= END_DATE]
rebalance_dates = backtest_dates[::7]  # REBALANCE_INTERVAL = 7

print("Actual rebalance dates (from backtest_dates[::7]):")
for i, rd in enumerate(rebalance_dates):
    print(f"  Rd #{i+1}: {rd}")

print()

# Get buy2 signals per stock
stock_buy2_dates = {}
for code, df in code_klines.items():
    dates_arr = df["日期"].values
    close_v = df["收盘"].values.astype(np.float64)
    high_v = df["最高"].values.astype(np.float64)
    low_v = df["最低"].values.astype(np.float64)
    vol_v = df["成交量"].values.astype(np.float64)
    n = len(df)
    ind = precompute_indicators(close_v, high_v, low_v, vol_v, n)
    buy2_set = detect_buy2_dates(close_v, high_v, low_v, vol_v, dates_arr, ind)
    if buy2_set:
        stock_buy2_dates[code] = sorted(buy2_set, key=lambda x: pd.Timestamp(x))

# For each rebalance date, find which stocks have buy2 active
print("Checking buy2 active windows vs rebalance dates:")
for rd_idx, rd in enumerate(rebalance_dates):
    rd_dt = pd.Timestamp(rd)
    start_dt = rd_dt - timedelta(days=5)
    end_dt = rd_dt + timedelta(days=2)
    
    overlap_stocks = []
    for code, b2_list in stock_buy2_dates.items():
        for b2_date in b2_list:
            b2_dt = pd.Timestamp(b2_date)
            b2_end = b2_dt + timedelta(days=BUY2_ACTIVE_DAYS - 1)
            if start_dt <= b2_end and b2_dt <= end_dt:
                overlap_stocks.append((code, b2_date))
                break
    
    print(f"  Rd #{rd_idx+1} {rd} window=[{start_dt.date()},{end_dt.date()}]: {len(overlap_stocks)} stocks with active buy2")
    if overlap_stocks and rd_idx >= 6:
        for code, b2 in overlap_stocks[:3]:
            print(f"    {code} buy2={b2}")
