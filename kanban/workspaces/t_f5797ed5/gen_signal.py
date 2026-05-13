#!/usr/bin/env python3
"""Generate /tmp/midcap_signal.json from factor matrix + compute composite scores."""
import pandas as pd
import numpy as np
import json
import time
from datetime import date
import sys

# Load factor matrix
df = pd.read_parquet('/home/pebynn/tmp/factor_matrix_20260513.parquet')
print(f'[gen] Loaded {len(df)} stocks from factor matrix', file=sys.stderr)

# Build composite score: weighted sum of L1 + L2 (buy2) + L3
# Normalize each to 0-100
df['l1_score_norm'] = ((df['l1_total'] - df['l1_total'].min()) / 
                       (df['l1_total'].max() - df['l1_total'].min()) * 100) if df['l1_total'].max() > df['l1_total'].min() else 50

# buy2_score is already 0-100 scale
df['l2_score_norm'] = df['buy2_score'].fillna(0)

# L3 normalize
df['l3_score_norm'] = ((df['l3_total'] - df['l3_total'].min()) / 
                       (df['l3_total'].max() - df['l3_total'].min()) * 100) if df['l3_total'].max() > df['l3_total'].min() else 50

# Composite: 30% L1 + 40% L2 (缠论二买 being the core signal) + 30% L3
weights = {'l1': 0.30, 'l2': 0.40, 'l3': 0.30}
df['composite'] = (df['l1_score_norm'] * weights['l1'] + 
                   df['l2_score_norm'] * weights['l2'] + 
                   df['l3_score_norm'] * weights['l3'])

# Sort by composite descending
df = df.sort_values('composite', ascending=False).reset_index(drop=True)

print(f'[gen] Composite range: {df["composite"].min():.1f} ~ {df["composite"].max():.1f}', file=sys.stderr)

# Also check for market_cap/close columns
extra_cols = [c for c in df.columns if c not in ['code','name','industry','l1_total','buy2_score','l3_total',
                                                   'l1_score_norm','l2_score_norm','l3_score_norm','composite',
                                                   'market','buy2_date','buy2_price','buy2_level','buy2_atr',
                                                   'buy2_vol_ratio','buy2_pullback','buy1_date','buy1_price']]
print(f'[gen] Additional columns: {extra_cols}', file=sys.stderr)

# Check for market_cap or close
for c in ['market_cap','close','pe_ttm','pb','roe_ttm','rev_growth','debt_ratio']:
    if c in df.columns:
        print(f'[gen] Found column: {c}', file=sys.stderr)

# Build signal records
signals = []
for _, row in df.iterrows():
    sig = {
        'code': row['code'],
        'name': row['name'],
        'industry': row.get('industry', ''),
        'composite': float(round(row['composite'], 2)),
        'l1_total': float(round(row['l1_total'], 4)),
        'buy2_score': int(row['buy2_score']) if pd.notna(row.get('buy2_score')) else None,
        'l3_total': float(round(row['l3_total'], 2)),
        'buy2_date': str(row.get('buy2_date', '')) if pd.notna(row.get('buy2_date')) else None,
        'buy2_price': float(round(row['buy2_price'], 2)) if pd.notna(row.get('buy2_price')) else None,
        'l1_score_norm': float(round(row['l1_score_norm'], 1)),
        'l3_score_norm': float(round(row['l3_score_norm'], 1)),
    }
    # Add optional columns if they exist
    for c in ['market_cap','close','pe_ttm','pb']:
        if c in df.columns and pd.notna(row.get(c)):
            sig[c] = float(row[c])
    signals.append(sig)

# Top 20
top20 = signals[:20]

# Stats
l1_positive = int((df['l1_total'] > 0).sum())
l3_positive = int((df['l3_total'] > 0).sum())
l2_count = int((df['buy2_score'] > 75).sum())
l2_strong = int((df['buy2_score'] >= 90).sum())

# Industry distribution
ind_dist = df.groupby('industry').size().sort_values(ascending=False).to_dict()
ind_dist_top = {k: int(v) for k, v in list(ind_dist.items())[:15]}

# Industry breakdown of top 20
top20_ind_dist = df.head(20).groupby('industry').size().sort_values(ascending=False).to_dict()
top20_ind_dist = {k: int(v) for k, v in top20_ind_dist.items()}

result = {
    'date': date.today().isoformat(),
    'index': {
        'code': '000905',
        'name': '中证500',
        'pct_chg': None,
    },
    'scan_info': {
        'total_candidates': 4939,
        'signals_found': len(signals),
        'mid_cap_filter': '50亿~400亿',
        'elapsed_sec': None,
        'source': 'factor_matrix_20260513.parquet',
    },
    'signals': signals,
    'top20': top20,
    'stats': {
        'total_signals': len(signals),
        'l1_positive': l1_positive,
        'l2_buy2_triggers': l2_count,
        'l2_strong_signals': l2_strong,
        'l3_positive': l3_positive,
    },
    'industry_distribution': ind_dist_top,
    'top20_industry_distribution': top20_ind_dist,
    'composite_weights': weights,
}

# Write to file
output_path = '/tmp/midcap_signal.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)

print(f'[gen] Written {output_path} ({len(signals)} signals, top20 weight sorted)', file=sys.stderr)
print(f'[gen] Stats: L2={l2_count}, L2_strong={l2_strong}, L1_pos={l1_positive}, L3_pos={l3_positive}', file=sys.stderr)
print(f'[gen] Top3: {signals[0]["code"]} {signals[0]["name"]} (composite={signals[0]["composite"]}), {signals[1]["code"]} {signals[1]["name"]} (composite={signals[1]["composite"]}), {signals[2]["code"]} {signals[2]["name"]} (composite={signals[2]["composite"]})', file=sys.stderr)

# Print top20 summary for verification
print(f'\n=== TOP 20 ===', file=sys.stderr)
for i, s in enumerate(top20[:10]):
    print(f'  {i+1}. {s["code"]} {s["name"]:8s} | composite={s["composite"]:5.1f} L1={s["l1_total"]:.3f} L2={s["buy2_score"]} L3={s["l3_total"]:.1f}', file=sys.stderr)
