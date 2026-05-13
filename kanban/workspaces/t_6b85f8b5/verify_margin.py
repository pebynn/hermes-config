#!/usr/bin/env python3
"""Verify margin data - test with known good date and today."""
import sys
sys.path.insert(0, "/home/pebynn/quant")
from margin_data import fetch_margin_daily

# Test with the last known good date
print("=== 2026-05-08 (last cached) ===")
df = fetch_margin_daily("2026-05-08")
if df is not None:
    print(f"Rows: {len(df)}")
else:
    print("No data")

# Test with today
print("\n=== 2026-05-13 (today) ===")
df2 = fetch_margin_daily("2026-05-13")
if df2 is not None:
    print(f"Rows: {len(df2)}")
else:
    print("No data")
