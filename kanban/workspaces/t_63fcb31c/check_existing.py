#!/home/pebynn/tools/quant_env/bin/python3
import sys
sys.path.insert(0, '/home/pebynn/quant')
from data_common import _get_db_engine
import pandas as pd

engine = _get_db_engine()

# Check if today's data exists
r = pd.read_sql("SELECT id, signal_date FROM daily_signal WHERE signal_date = '2026-05-13'", engine)
print(f'daily_signal today: {len(r)} rows')
print(r.to_string() if len(r) > 0 else 'None')

r2 = pd.read_sql("SELECT id, signal_date FROM daily_signal_detail WHERE signal_date = '2026-05-13'", engine)
print(f'\ndaily_signal_detail today: {len(r2)} rows')
print(r2.to_string() if len(r2) > 0 else 'None')

# Also check zz500 reference
r3 = pd.read_sql("SHOW TABLES LIKE 'stock_index%'", engine)
print(f'\nIndex tables:')
print(r3.to_string() if len(r3) > 0 else 'None')
