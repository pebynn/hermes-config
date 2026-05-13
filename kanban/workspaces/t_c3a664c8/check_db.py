#!/home/pebynn/tools/quant_env/bin/python3
import sys, os
sys.path.insert(0, "/home/pebynn/quant")
os.chdir("/home/pebynn/quant")
from data_common import _get_db_engine
import pandas as pd

engine = _get_db_engine()
cnt = pd.read_sql("SELECT COUNT(*) as n FROM kline", engine)
stocks = pd.read_sql("SELECT COUNT(DISTINCT code) as n FROM kline", engine)
engine.dispose()
print(f"Kline rows: {cnt.iloc[0]['n']:,}")
print(f"Unique stocks: {stocks.iloc[0]['n']:,}")
