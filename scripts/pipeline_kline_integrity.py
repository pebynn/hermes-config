#!/usr/bin/env python3
"""pipeline_kline_integrity.py — 每周五检查K线缓存连续性"""
import sys, subprocess
from pathlib import Path
import traceback

# 使用 quant_env 的 python3（有 pandas）
QUANT_PY = str(Path.home() / "tools" / "quant_env" / "bin" / "python3")
if sys.executable != QUANT_PY and Path(QUANT_PY).exists():
    r = subprocess.run([QUANT_PY] + sys.argv)
    sys.exit(r.returncode)

from datetime import datetime, timedelta
import pandas as pd

KLINE_DIR = Path.home() / '.finquant' / 'cache' / 'kline'

today = datetime.now()
weekday = today.weekday()

print(f"K线缓存完整性检查 ({today.date()})")
print(f"{'='*50}")

if weekday != 4:
    print(f"  今日不是周五 (周{weekday+1})，跳过全量检查")
    exit(0)

# 最近5个交易日
trading_dates = []
d = today
while len(trading_dates) < 5:
    if d.weekday() < 5:
        trading_dates.append(d)
    d -= timedelta(days=1)

print(f"  检查周期: {trading_dates[-1].date()} ~ {trading_dates[0].date()}")

# 抽样检查
parquets = list(KLINE_DIR.glob('k_*.parquet'))
sample = parquets[:100]

missing_dates = []
for p in sample:
    try:
        df = pd.read_parquet(p)
        dates = set(df['日期'].astype(str).tolist())
        for td in trading_dates:
            ds = td.strftime('%Y-%m-%d')
            if ds not in dates:
                missing_dates.append((p.name, ds))
    except:
        traceback.print_exc()
        pass

print(f"\n  抽样 {len(sample)} 只股票")
if missing_dates:
    print(f"  ⚠️ {len(missing_dates)} 个缺失 (抽样率 {len(sample)}/{len(parquets)})")
    for f, d in missing_dates[:5]:
        print(f"    {f}: 缺 {d}")
else:
    print(f"  ✅ 抽样均完整，K线缓存连续")
