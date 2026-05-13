#!/usr/bin/env python3
import pandas as pd
df = pd.read_parquet('/home/pebynn/tmp/factor_matrix_20260513.parquet')
print('Shape:', df.shape)
print('Columns:', list(df.columns))
print()
# Show sample values
print('First 3 rows (key columns):')
key_cols = [c for c in df.columns if c in ['code','name','industry','market_cap','close','pe_ttm','pb','roe_ttm','rev_growth','debt_ratio']]
extra_cols = ['composite','l1_total','buy2_score','l3_total','l4_total','l2_rating']
for c in extra_cols:
    if c in df.columns:
        key_cols.append(c)
print(df[key_cols].head(3).to_string())
print()
# Check industry distribution
if 'industry' in df.columns:
    print('Industry distribution (top 15):')
    print(df['industry'].value_counts().head(15).to_string())
print()
# Check sorting columns
for c in ['composite','buy2_score','l1_total']:
    if c in df.columns:
        print(f'{c} range: {df[c].min():.2f} ~ {df[c].max():.2f} (non-null: {df[c].notna().sum()})')
