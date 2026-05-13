#!/usr/bin/env python3
"""Test that daily_kline_update.py imports correctly."""
import sys
sys.path.insert(0, '/home/pebynn/quant')
try:
    from daily_kline_update import main
    print('IMPORT_OK: daily_kline_update.main() found')
except ImportError as e:
    print(f'IMPORT_FAILED: {e}')
except Exception as e:
    print(f'OTHER_ERROR: {e}')
