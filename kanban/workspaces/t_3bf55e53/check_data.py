#!/home/pebynn/tools/quant_env/bin/python3
"""Check data volume for backtest planning."""
import os, sys
import pandas as pd
sys.path.insert(0, "/home/pebynn/quant")
from data_common import _get_db_engine

engine = _get_db_engine()
if engine:
    cnt = pd.read_sql('SELECT COUNT(*) as n FROM kline WHERE trade_date >= "2025-04-01" AND trade_date <= "2026-04-30"', engine)
    stocks = pd.read_sql('SELECT COUNT(DISTINCT code) as n FROM kline WHERE trade_date >= "2025-04-01" AND trade_date <= "2026-04-30"', engine)
    dates = pd.read_sql('SELECT COUNT(DISTINCT trade_date) as n FROM kline WHERE trade_date >= "2025-04-01" AND trade_date <= "2026-04-30"', engine)
    print(f"Kline rows: {cnt.iloc[0,0]:,}")
    print(f"Unique stocks: {stocks.iloc[0,0]:,}")
    print(f"Trading days: {dates.iloc[0,0]}")
    engine.dispose()

# Check sina parquet
sina_path = "/home/pebynn/quant/cache/sina_kline_2025_2026.parquet"
if os.path.exists(sina_path):
    size_mb = os.path.getsize(sina_path) / 1024 / 1024
    df = pd.read_parquet(sina_path)
    print(f"\nSina parquet: {size_mb:.1f} MB, {len(df):,} rows, {df['code'].nunique()} stocks, {df['trade_date'].nunique()} days")
    print(f"Memory estimate: {df.memory_usage(deep=True).sum() / 1024 / 1024:.0f} MB")
else:
    print("\nSina parquet not found")
