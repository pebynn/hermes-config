import pandas as pd
# Compare yesterday's good data vs today's zero data
yesterday = pd.read_parquet('/home/pebynn/.finquant/cache/fund_flow/fund_flow_2026-05-12.parquet')
today = pd.read_parquet('/home/pebynn/.finquant/cache/fund_flow/fund_flow_2026-05-13.parquet')

print("=== YESTERDAY (2026-05-12, good data) ===")
print(f"Shape: {yesterday.shape}")
print(f"Columns: {list(yesterday.columns)}")
print(f"Non-zero main_net: {(yesterday['main_net'] != 0).sum()}")
if 'retail_net' in yesterday.columns:
    print(f"Non-zero retail_net: {(yesterday['retail_net'] != 0).sum()}")
print(f"File size: 11,327 bytes")
print()
print(yesterday.head(5).to_string())
print()

print("=== TODAY (2026-05-13, zero data) ===")
print(f"Shape: {today.shape}")
print(f"Columns: {list(today.columns)}")
print(f"Non-zero main_net: {(today['main_net'] != 0).sum()}")
print(f"File size: 6,321 bytes")
print()
print(today.head(5).to_string())
