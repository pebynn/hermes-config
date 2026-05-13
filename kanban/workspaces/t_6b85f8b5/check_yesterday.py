#!/usr/bin/env python3
"""Check if yesterday's (2026-05-12) margin data is now available."""
import sys
sys.path.insert(0, "/home/pebynn/quant")
from margin_data import fetch_margin_daily

# Test yesterday
print("=== 2026-05-12 (yesterday) ===")
df = fetch_margin_daily("2026-05-12")
if df is not None:
    print(f"Rows: {len(df)}")
else:
    print("No data")

print("\n=== 2026-05-11 (day before) ===")
df2 = fetch_margin_daily("2026-05-11")
if df2 is not None:
    print(f"Rows: {len(df2)}")
else:
    print("No data")
