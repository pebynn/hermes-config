#!/usr/bin/env python3
"""P3-信号扫描排名-2026-05-13
Pipeline: 加载因子矩阵 → L2质量门(score>=75) → 行业中性化 → 综合评分 → Top20 → 输出JSON
"""
import pandas as pd
import numpy as np
import json
import sys
from scipy import stats

# ─── 1. 加载因子矩阵 ───
INPUT_PARQUET = '/home/pebynn/tmp/factor_matrix_20260513.parquet'
OUTPUT_JSON = '/tmp/midcap_signal.json'

df = pd.read_parquet(INPUT_PARQUET)
print(f"1. 原始数据: {len(df)} 只, {len(df.columns)} 列")

# ─── 2. L2质量门 (因子矩阵已含L2筛选,全部>=75) ───
assert df['buy2_score'].min() >= 75, "L2质量门异常!"
print(f"   L2质量门: min={df['buy2_score'].min()}, max={df['buy2_score'].max()}, 全部通过 ✓")

# ─── 3. 处理缺失值 ───
# l1_net_margin, l1_profit_growth 全部NaN → 0
df['l1_net_margin'] = df['l1_net_margin'].fillna(0)
df['l1_profit_growth'] = df['l1_profit_growth'].fillna(0)

# l1_ep, l1_bp 部分NaN → 中位数
for col in ['l1_ep', 'l1_bp']:
    med = df[col].median()
    df[col] = df[col].fillna(med)
    print(f"   {col}: NaN → 中位数={med:.6f}")

print(f"   缺失值处理完成 ✓")

# ─── 4. 综合评分(各维百分位归一化后加权) ───
weights = {'L1': 0.25, 'L2': 0.30, 'FF': 0.20, 'L3': 0.25}

# 直接使用因子矩阵的复合分数: l1_total, buy2_score, ff_score, l3_total
df['L1_norm'] = df['l1_total'].rank(pct=True, method='average')
df['L2_norm'] = df['buy2_score'].rank(pct=True, method='average')
df['FF_norm'] = df['ff_score'].rank(pct=True, method='average')
df['L3_norm'] = df['l3_total'].rank(pct=True, method='average')

df['raw_score'] = (
    df['L1_norm'] * weights['L1'] +
    df['L2_norm'] * weights['L2'] +
    df['FF_norm'] * weights['FF'] +
    df['L3_norm'] * weights['L3']
)

print(f"\n4. 综合评分:")
print(f"   权重: L1×{weights['L1']} + L2×{weights['L2']} + 资金流×{weights['FF']} + L3×{weights['L3']}")
print(f"   raw_score: {df['raw_score'].min():.4f} ~ {df['raw_score'].max():.4f}")

# ─── 5. 行业中性化 ───
# ≥3只的行业: 减去行业均值 (对齐行业内偏离度)
# <3只的行业: 减去全市场均值 (样本不足以估算行业均值,用全局均值替代)
industry_counts = df['industry'].value_counts()
small_ind = industry_counts[industry_counts < 3].index.tolist()
global_mean = df['raw_score'].mean()
print(f"\n5. 行业中性化: {len(industry_counts)}行业, <3只: {len(small_ind)}个")
print(f"   全市场raw_score均值={global_mean:.4f}")

df['neutralized_score'] = df['raw_score'].copy()
for ind, grp in df.groupby('industry'):
    if len(grp) >= 3:
        ind_mean = grp['raw_score'].mean()
        df.loc[df['industry'] == ind, 'neutralized_score'] = grp['raw_score'] - ind_mean
    else:
        # 小行业: 用全局均值替代行业均值
        df.loc[df['industry'] == ind, 'neutralized_score'] = grp['raw_score'] - global_mean
df['rank'] = df['neutralized_score'].rank(ascending=False, method='min').astype(int)
print(f"   中性化后: {df['neutralized_score'].min():.4f} ~ {df['neutralized_score'].max():.4f}")

# ─── 6. Top 20 ───
top20 = df.nsmallest(20, 'rank')  # rank 1 = best

# 分量百分位(×100)
top20['L1_pct'] = (top20['L1_norm'] * 100).round(1)
top20['L2_pct'] = (top20['L2_norm'] * 100).round(1)
top20['FF_pct'] = (top20['FF_norm'] * 100).round(1)
top20['L3_pct'] = (top20['L3_norm'] * 100).round(1)

print(f"\n6. Top 20 信号:")
print(f"   {'#':>3s} {'代码':6s} {'名称':8s} {'行业':8s} {'得分':>8s}  L1%  L2%  FF%  L3%  buy2 ff l3tot")
print(f"   {'-'*60}")
for _, r in top20.iterrows():
    print(f"   #{r['rank']:2d} {r['code']} {r['name']:8s} {r['industry']:8s} "
          f"{r['neutralized_score']:8.4f}  "
          f"{r['L1_pct']:3.0f} {r['L2_pct']:3.0f} {r['FF_pct']:3.0f} {r['L3_pct']:3.0f}  "
          f"{r['buy2_score']} {r['ff_score']:.0f} {r['l3_total']:.0f}")

# ─── 7. 输出 JSON ───
output = {
    "date": "2026-05-13",
    "pipeline": "P3-信号扫描排名",
    "total_screened": len(df),
    "total_industries": len(industry_counts),
    "weights": weights,
    "normalization": "percentile_rank",
    "neutralization": "industry_mean_subtract (>=3 stocks)",
    "L2_quality_gate": "buy2_score >= 75",
    "top20": []
}

for _, r in top20.iterrows():
    output["top20"].append({
        "rank": int(r['rank']),
        "code": r['code'],
        "name": r['name'],
        "industry": r['industry'],
        "neutralized_score": round(float(r['neutralized_score']), 4),
        "components": {
            "L1_pct": float(r['L1_pct']),
            "L2_pct": float(r['L2_pct']),
            "FF_pct": float(r['FF_pct']),
            "L3_pct": float(r['L3_pct']),
        },
        "raw_data": {
            "buy2_score": int(r['buy2_score']),
            "buy2_price": float(r['buy2_price']),
            "l1_total": float(r['l1_total']),
            "l1_ep": float(r['l1_ep']),
            "l1_bp": float(r['l1_bp']),
            "l1_mom_12m": float(r['l1_mom_12m']),
            "l1_reversal_1m": float(r['l1_reversal_1m']),
            "ff_score": float(r['ff_score']),
            "ff_main_net": float(r['ff_main_net']),
            "l3_total": float(r['l3_total']),
            "l3_mfi": float(r['l3_mfi']),
            "l3_kama": float(r['l3_kama']),
        }
    })

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

json_size = len(json.dumps(output, ensure_ascii=False))
print(f"\n7. 输出 {OUTPUT_JSON} ✓ ({json_size:,} 字节)")
print(f"\n{'='*50}")
print(f"   P3 信号扫描排名 DONE")
print(f"   {len(df)} 只 → 行业中性化 → Top 20")
print(f"{'='*50}")
