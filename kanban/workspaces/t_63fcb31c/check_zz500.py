#!/home/pebynn/tools/quant_env/bin/python3
import sys
sys.path.insert(0, '/home/pebynn/quant')
from data_common import _get_db_engine
import pandas as pd

engine = _get_db_engine()

# Check what index/zz500 data exists
r = pd.read_sql("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'stock_kline' AND TABLE_NAME LIKE CONCAT('%', 'index', '%')", engine)
print('Index tables:', r.to_dict())

# Try zz500 daily data
try:
    r2 = pd.read_sql("SELECT * FROM stock_index_daily WHERE index_code = '000905' ORDER BY trade_date DESC LIMIT 1", engine)
    print('\nzz500 latest:', r2.to_dict() if len(r2) > 0 else 'Empty')
except Exception as e:
    print(f'stock_index_daily: {e}')
    
# Also try kline for 000905 (zz500 ETF)
try:
    r3 = pd.read_sql("SELECT DISTINCT code FROM kline WHERE code = '000905' LIMIT 1", engine)
    print(f'\n000905 in kline: {len(r3)}')
except Exception as e:
    print(f'kline check: {e}')
