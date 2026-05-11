#!/bin/bash
# L4两融数据拉取 — 16:15运行
# 拉取当日两融数据并缓存

set -e
cd /home/pebynn/quant

TODAY=$(date +%F)
CACHE_FILE="$HOME/.finquant/cache/margin/${TODAY}.parquet"

if [ -f "$CACHE_FILE" ]; then
    echo "[margin_precache] 缓存已存在: $CACHE_FILE"
    ROWS=$(/home/pebynn/tools/quant_env/bin/python3 -c "import pandas as pd; print(len(pd.read_parquet('$CACHE_FILE')))" 2>/dev/null)
    echo "[margin_precache] $ROWS 只"
    exit 0
fi

echo "[margin_precache] 拉取 $TODAY 两融数据..."
/home/pebynn/tools/quant_env/bin/python3 -c "
import sys; sys.path.insert(0, '.')
from margin_data import fetch_and_cache_today
ok = fetch_and_cache_today()
print(f'两融采集{\"成功\" if ok else \"失败\"}')
" 2>&1

if [ -f "$CACHE_FILE" ]; then
    ROWS=$(/home/pebynn/tools/quant_env/bin/python3 -c "import pandas as pd; print(len(pd.read_parquet('$CACHE_FILE')))" 2>/dev/null)
    echo "[margin_precache] 成功: $CACHE_FILE ($ROWS 只)"
else
    echo "[margin_precache] 无数据（可能非交易日）"
fi
