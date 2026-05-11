#!/bin/bash
# 资金流预采集 — 收盘后15:05运行
# 为21:00信号扫描提供缓存数据

set -e
cd /home/pebynn/quant

# 获取当前日期
TODAY=$(date +%F)

# 步骤1: 检查缓存是否已存在
CACHE_FILE="$HOME/.finquant/cache/fund_flow/fund_flow_${TODAY}.parquet"
if [ -f "$CACHE_FILE" ]; then
    echo "[fund_flow_precache] 缓存已存在: $CACHE_FILE"
    exit 0
fi

# 步骤2: 获取中盘股列表（50亿~400亿）
echo "[fund_flow_precache] 获取中盘股列表..."
MID_STOCKS=$(/home/pebynn/tools/quant_env/bin/python3 -c "
import sys; sys.path.insert(0, '.')
from data_common import get_stock_list
import pandas as pd
stocks = get_stock_list('all')
codes = stocks['code'].tolist()
print(','.join(codes[:2000]))
" 2>/dev/null)

if [ -z "$MID_STOCKS" ]; then
    echo "[fund_flow_precache] 获取股票列表失败"
    exit 1
fi

# 步骤3: 通过 stock_fund_flow 拉取并缓存
echo "[fund_flow_precache] 执行 stock_fund_flow 预采集..."
/home/pebynn/tools/quant_env/bin/python3 -c "
import sys; sys.path.insert(0, '.')
from stock_fund_flow import fetch_and_cache_today
stock_list = '$MID_STOCKS'.split(',')
ok = fetch_and_cache_today(stock_list=stock_list)
print(f'采集{\"成功\" if ok else \"失败\"}')
" 2>&1

# 如果上面的 stock-sdk 方式失败，fallback: 使用 precache_fund_flow_full.py 的全量采集
if [ ! -f "$CACHE_FILE" ]; then
    echo "[fund_flow_precache] stock-sdk 方式失败，尝试全量东方财富 API..."
    /home/pebynn/tools/quant_env/bin/python3 /home/pebynn/quant/precache_fund_flow_full.py 2>&1
fi

# 验证
if [ -f "$CACHE_FILE" ]; then
    ROWS=$(/home/pebynn/tools/quant_env/bin/python3 -c "import pandas as pd; print(len(pd.read_parquet('$CACHE_FILE')))" 2>/dev/null)
    echo "[fund_flow_precache] 成功: $CACHE_FILE ($ROWS 只)"
else
    echo "[fund_flow_precache] 失败: 无法创建缓存文件"
fi
