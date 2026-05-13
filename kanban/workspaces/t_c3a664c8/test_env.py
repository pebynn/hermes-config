#!/home/pebynn/tools/quant_env/bin/python3
import sys
sys.path.insert(0, "/home/pebynn/quant")
from data_common import _get_db_engine
print("data_common OK")
import pandas as pd
print("pandas OK")
import numpy as np
print("numpy OK")
engine = _get_db_engine()
cnt = pd.read_sql("SELECT COUNT(*) as n FROM kline", engine)
print(f"Kline records: {cnt.iloc[0]['n']:,}")
engine.dispose()
