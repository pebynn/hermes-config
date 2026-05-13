#!/home/pebynn/tools/quant_env/bin/python3
import sys
sys.path.insert(0, '/home/pebynn/quant')
from data_common import _get_db_engine
import pandas as pd

engine = _get_db_engine()

# Get all tables
tables = pd.read_sql("SHOW TABLES", engine)
print('=== All Tables ===')
print(tables.to_string())

# daily_signal
print('\n=== daily_signal DESC ===')
try:
    desc = pd.read_sql("DESCRIBE daily_signal", engine)
    print(desc.to_string())
except Exception as e:
    print(f'Error: {e}')

# daily_signal_detail
print('\n=== daily_signal_detail DESC ===')
try:
    desc = pd.read_sql("DESCRIBE daily_signal_detail", engine)
    print(desc.to_string())
except Exception as e:
    print(f'Error: {e}')
