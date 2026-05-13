#!/usr/bin/env python3
"""Test key functions from daily_kline_update without full execution."""
import sys, json
sys.path.insert(0, '/home/pebynn/quant')
from data_common import get_stock_list
df = get_stock_list(market='all')
print(f"STOCK_LIST: {len(df)} stocks, columns: {list(df.columns)}")
