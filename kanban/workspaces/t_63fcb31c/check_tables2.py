#!/home/pebynn/tools/quant_env/bin/python3
import sys
sys.path.insert(0, '/home/pebynn/quant')
from data_common import _get_db_engine
import pandas as pd
engine = _get_db_engine()
tables = pd.read_sql('SHOW TABLES', engine)
print('=== All Tables ===')
print(tables.to_string())

# Check for signal-related tables
sig_tables = pd.read_sql("SHOW TABLES LIKE '%signal%'", engine)
print('\n=== Signal Tables ===')
print(sig_tables.to_string())

# Check for daily related tables
daily_tables = pd.read_sql("SHOW TABLES LIKE '%daily%'", engine)
print('\n=== Daily Tables ===')
print(daily_tables.to_string())

# Check for result related tables
result_tables = pd.read_sql("SHOW TABLES LIKE '%result%'", engine)
print('\n=== Result Tables ===')
print(result_tables.to_string())
