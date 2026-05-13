#!/home/pebynn/tools/quant_env/bin/python3
"""Verify factor matrix output parquet."""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

path = Path.home() / 'tmp' / 'factor_matrix_20260513.parquet'
print(f"File: {path}")
print(f"Size: {path.stat().st_size / 1024:.0f} KB")

df = pd.read_parquet(path)
print(f"\n=== Basic Stats ===")
print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
print(f"Columns: {list(df.columns)}")

print(f"\n=== L2 Buy2 Score Distribution ===")
if 'buy2_score' in df.columns:
    print(df['buy2_score'].describe())
    print(f"  Strong (>=80): {(df['buy2_score'] >= 80).sum()}")
    print(f"  Medium (75-79): {((df['buy2_score'] >= 75) & (df['buy2_score'] < 80)).sum()}")

print(f"\n=== L1 Factor Stats ===")
l1_cols = [c for c in df.columns if c.startswith('l1_') and c != 'l1_total']
for col in l1_cols:
    valid = df[col].notna().sum()
    non_nan_pct = valid / len(df) * 100
    if valid > 0:
        print(f"  {col}: {valid}/{len(df)} valid ({non_nan_pct:.0f}%), "
              f"mean={df[col].mean():.4f}, median={df[col].median():.4f}")
    else:
        print(f"  {col}: 0 valid (ALL NaN)")

print(f"\n=== L1 Total Score ===")
if 'l1_total' in df.columns:
    print(f"  mean={df['l1_total'].mean():.4f}, median={df['l1_total'].median():.4f}")
    print(f"  range: {df['l1_total'].min():.4f} - {df['l1_total'].max():.4f}")

print(f"\n=== L3 Factor Stats ===")
l3_cols = [c for c in df.columns if c.startswith('l3_')]
for col in l3_cols:
    valid = df[col].notna().sum()
    non_nan_pct = valid / len(df) * 100
    if valid > 0:
        print(f"  {col}: mean={df[col].mean():.4f}, median={df[col].median():.4f}")

print(f"\n=== Fund Flow Stats ===")
ff_cols = [c for c in df.columns if c.startswith('ff_')]
for col in ff_cols:
    valid = df[col].notna().sum()
    non_zero = (df[col] != 0).sum() if valid > 0 else 0
    print(f"  {col}: mean={df[col].mean():.4f}, non-zero={non_zero}/{len(df)}")

print(f"\n=== Industry Coverage ===")
if 'industry' in df.columns:
    top_industries = df['industry'].value_counts().head(10)
    print(f"Top 10 industries:")
    for ind, cnt in top_industries.items():
        print(f"  {ind}: {cnt}")

print(f"\n=== Buy2 Date Distribution ===")
if 'buy2_date' in df.columns:
    date_counts = df['buy2_date'].value_counts().sort_index()
    print(f"Date range: {date_counts.index[0]} ~ {date_counts.index[-1]}")
    print("By date:")
    for d, c in date_counts.items():
        print(f"  {d}: {c} stocks")
