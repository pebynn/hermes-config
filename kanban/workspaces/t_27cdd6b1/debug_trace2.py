"""Deep debug: trace buy2 signals + entry conditions for Sina backtest."""
import sys, os
sys.path.insert(0, '/home/pebynn/quant')
import pandas as pd
import numpy as np
from datetime import timedelta

# Import the actual functions
from strategy_chan import precompute_indicators, detect_buy2_dates, check_entry_conditions

SINA_PARQUET_PATH = '/home/pebynn/quant/cache/sina_kline_2025_2026.parquet'
START_DATE = "2026-01-01"
END_DATE = "2026-04-30"
WARMUP_DAYS = 200
BUY2_ACTIVE_DAYS = 12
VOL_RATIO_MIN = 2.0
REBALANCE_INTERVAL = 7
MAX_HOLDINGS = 8
MIN_HOLDINGS = 6
STOP_LOSS = -0.08
TAKE_PROFIT = 0.10
MAX_HOLD_DAYS = 30

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

# Pre-compute buy2 signals (same as main())
stock_buy2_active = {}
stock_indicators = {}
stock_date_to_idx = {}

for code, df in code_klines.items():
    dates_arr = df["日期"].values
    close_v = df["收盘"].values.astype(np.float64)
    high_v = df["最高"].values.astype(np.float64)
    low_v = df["最低"].values.astype(np.float64)
    vol_v = df["成交量"].values.astype(np.float64)
    n = len(df)
    
    d2i = {str(d): i for i, d in enumerate(dates_arr)}
    stock_date_to_idx[code] = d2i
    
    ind = precompute_indicators(close_v, high_v, low_v, vol_v, n)
    stock_indicators[code] = ind
    
    buy2_set = detect_buy2_dates(close_v, high_v, low_v, vol_v, dates_arr, ind)
    if buy2_set:
        buy2_dt_sorted = sorted(pd.Timestamp(d) for d in buy2_set)
        active_set = set()
        for dt in buy2_dt_sorted:
            active_set.add(dt.strftime("%Y-%m-%d"))
            for dd in range(1, BUY2_ACTIVE_DAYS):
                active_set.add((dt + timedelta(days=dd)).strftime("%Y-%m-%d"))
        stock_buy2_active[code] = active_set

print(f"Stocks with buy2 signals: {len(stock_buy2_active)}")

# Now trace rebalance
all_dates = sorted(set(d for code in code_klines for d in code_klines[code]["日期"].values), key=lambda x: pd.Timestamp(x))
backtest_dates = [d for d in all_dates if START_DATE <= d <= END_DATE]
rebalance_dates = backtest_dates[::REBALANCE_INTERVAL]
print(f"Rebalance dates: {len(rebalance_dates)}")

for rd_idx, rd in enumerate(rebalance_dates):
    rd_dt = pd.Timestamp(rd)
    start_dt = rd_dt - timedelta(days=5)
    end_dt = rd_dt + timedelta(days=2)
    
    candidates = 0
    skipped_no_active = 0
    skipped_no_condition = 0
    skipped_not_in_data = 0
    
    for code in stock_buy2_active:
        if code not in code_klines:
            skipped_not_in_data += 1
            continue
        
        d2i = stock_date_to_idx[code]
        
        # Check buy2 active window
        has_active = False
        for check_date in backtest_dates:
            check_dt = pd.Timestamp(check_date)
            if start_dt <= check_dt <= end_dt and check_date in stock_buy2_active.get(code, set()):
                has_active = True
                break
        if not has_active:
            skipped_no_active += 1
            continue
        
        # Check entry conditions  
        df = code_klines[code]
        close_v = df["收盘"].values.astype(np.float64)
        vol_v = df["成交量"].values.astype(np.float64)
        ind = stock_indicators[code]
        
        found = False
        for check_date in backtest_dates:
            check_dt = pd.Timestamp(check_date)
            if check_dt < start_dt or check_dt > end_dt:
                continue
            if check_date not in stock_buy2_active[code]:
                continue
            if check_date not in d2i:
                continue
            i = d2i[check_date]
            
            if check_entry_conditions(ind, i, close_v, vol_v):
                candidates += 1
                found = True
                break
        
        if not found:
            skipped_no_condition += 1
    
    print(f"Rd #{rd_idx+1} {rd}: buy2_stocks={len(stock_buy2_active)} "
          f"no_active={skipped_no_active} no_cond={skipped_no_condition} "
          f"candidates={candidates}")
    
    if candidates > 0:
        print(f"  >>> CANDIDATES FOUND! min_required={MIN_HOLDINGS}")
    
    if rd_idx >= 5:
        print("  (stopping for brevity)")
        break
