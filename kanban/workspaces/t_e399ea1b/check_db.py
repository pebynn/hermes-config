import sys, pandas as pd
sys.path.insert(0, '/home/pebynn/quant')
from data_common import _get_db_engine
engine = _get_db_engine()
with engine.connect() as conn:
    r = pd.read_sql("SELECT MIN(trade_date) as mn, MAX(trade_date) as mx, COUNT(DISTINCT code) as cnt FROM kline", conn)
    print(f"Kline DB: min={r['mn'].iloc[0]} max={r['mx'].iloc[0]} stocks={r['cnt'].iloc[0]}")
    r = pd.read_sql("SELECT COUNT(*) as cnt FROM kline WHERE trade_date >= '2025-04-01' AND trade_date <= '2026-04-30'", conn)
    print(f"Rows in range: {r['cnt'].iloc[0]}")
    r = pd.read_sql("SELECT COUNT(DISTINCT code) as cnt FROM kline WHERE trade_date >= '2025-04-01'", conn)
    print(f"Stocks w/data: {r['cnt'].iloc[0]}")
