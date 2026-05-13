#!/home/pebynn/tools/quant_env/bin/python3
"""Quick test: verify critical imports work."""
import sys
sys.path.insert(0, '/home/pebynn/quant')

from data_common import get_stock_list, load_share_db, verify_write
codes = get_stock_list(market='all')
print(f'Stock list loaded: {len(codes)} stocks')
shares = load_share_db()
print(f'Share DB loaded: {len(shares)} stocks')

# Test main script imports
from daily_kline_update import fetch_all_tushare, update_cache_from_row
print('Main script imports OK')

# Test fallback imports
from kline_fallback import get_stock_kline, is_available as xq_is_available
print('Fallback imports OK')

print('ALL IMPORTS PASSED')
