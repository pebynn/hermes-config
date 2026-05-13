#!/usr/bin/env python3
"""Backfill margin cache for 2026-05-11 and 2026-05-12."""
import sys
sys.path.insert(0, "/home/pebynn/quant")
from margin_data import fetch_and_cache_date, MARGIN_CACHE_DIR
from pathlib import Path

dates = ["2026-05-11", "2026-05-12"]
for d in dates:
    cp = MARGIN_CACHE_DIR / f"{d}.parquet"
    if cp.exists():
        print(f"[OK] 缓存已存在: {d} ({cp.stat().st_size} bytes)")
        continue
    print(f"[FETCH] 补拉 {d} ...")
    ok = fetch_and_cache_date(d)
    if ok:
        print(f"[OK] 缓存成功: {d} ({cp.stat().st_size} bytes)")
    else:
        print(f"[FAIL] 补拉失败: {d}")
