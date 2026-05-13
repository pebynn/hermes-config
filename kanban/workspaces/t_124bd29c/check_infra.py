#!/home/pebynn/tools/quant_env/bin/python3
"""Quick infrastructure check for factor computation."""
import sys, os
sys.path.insert(0, '/home/pebynn/quant')
from data_common import get_stock_list, load_share_db, get_industry_map
from pathlib import Path
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

home = Path.home()

# Stock list
sl = get_stock_list(market='all')
print(f"[STOCK_LIST] {len(sl)} rows, columns: {list(sl.columns)}")
if len(sl) > 0:
    market_counts = sl['market'].value_counts().to_dict()
    print(f"  Market breakdown: {market_counts}")

sd = load_share_db()
print(f"[SHARE_DB] {len(sd)} stocks")

im = get_industry_map()
print(f"[INDUSTRY_MAP] {len(im)} stocks")

# Kline cache
kdir = home / ".finquant" / "cache" / "kline"
kfiles = list(kdir.glob("*.parquet"))
print(f"[KLINE] {len(kfiles)} parquet files")
if kfiles:
    sample = pd.read_parquet(kfiles[0])
    print(f"  Sample {kfiles[0].stem}: {len(sample)} rows, cols={list(sample.columns)[:10]}...")
    print(f"  Date range: {sample.iloc[0,0]} ~ {sample.iloc[-1,0]}")

# Financial cache
fdir = home / ".finquant" / "cache" / "financial"
ffiles = list(fdir.glob("*.parquet"))
print(f"[FINANCIAL] {len(ffiles)} parquet files")
if ffiles:
    sample_f = pd.read_parquet(ffiles[0])
    print(f"  Sample {ffiles[0].stem}: {len(sample_f)} rows, cols={list(sample_f.columns)}")

# Fund flow cache
ffdir = home / ".finquant" / "cache" / "fund_flow"
ffiles2 = list(ffdir.glob("*.parquet"))
print(f"[FUND_FLOW] {len(ffiles2)} parquet files")
for f in sorted(ffiles2):
    df = pd.read_parquet(f)
    nz = (df["main_net"] != 0).sum() if "main_net" in df.columns else "N/A"
    print(f"  {f.stem}: {len(df)} rows, main_net non-zero: {nz}")

# MySQL
from data_common import _get_db_engine
engine = _get_db_engine()
cnt = pd.read_sql('SELECT COUNT(*) as c FROM kline WHERE trade_date >= "2026-05-01"', engine)
print(f"[MYSQL] kline rows (May 2026+): {cnt.iloc[0,0]}")
cnt2 = pd.read_sql('SELECT COUNT(DISTINCT code) as c FROM kline', engine)
print(f"[MYSQL] distinct stocks: {cnt2.iloc[0,0]}")
cnt3 = pd.read_sql('SELECT MAX(trade_date) as md FROM kline', engine)
print(f"[MYSQL] max trade_date: {cnt3.iloc[0,0]}")

# Chan buy contract check
try:
    sys.path.insert(0, '/home/pebynn/quant')
    from contracts.chan_buy_contract import ChanBuySignalProvider
    print(f"[CHAN] ChanBuySignalProvider imported OK")
    # Test with a sample kline
    if kfiles:
        test_kl = pd.read_parquet(kfiles[0])
        buy2 = ChanBuySignalProvider.detect_chan_buy2(test_kl)
        if buy2 is not None and not buy2.empty:
            print(f"  {kfiles[0].stem}: buy2 signals={len(buy2)}, latest={buy2.iloc[-1].to_dict()}")
        else:
            print(f"  {kfiles[0].stem}: No buy2 signals")
except Exception as e:
    print(f"[CHAN] ERROR: {e}")

print("\n[DONE] Infrastructure check complete")
