#!/bin/bash
# 策略A v2 独立信号生成 — signal_a_v2_wrapper.sh
# Cron: 8 16 * * 1-5

set -euo pipefail
cd /home/pebynn/quant
PYTHON=/home/pebynn/tools/quant_env/bin/python3
TODAY=$(date +%Y-%m-%d)

echo "[$(date)] Strategy A v2 signal generation: $TODAY"

$PYTHON -c "
import sys, os, json
sys.path.insert(0, '/home/pebynn/quant')
from daily_signals import rank_strategy_A, load_kline
from data_common import _get_db_engine
import pandas as pd

target_date = '$TODAY'
engine = _get_db_engine()

# 加载中盘K线
panel = load_kline(engine, target_date, lookback_days=120)
engine.dispose()

if panel is None or len(panel) == 0:
    print('[SKIP] No kline data available')
    sys.exit(0)

# 生成策略A信号
all_dates = sorted(panel['trade_date'].unique())
signals = rank_strategy_A(panel, target_date, all_dates)

output = {
    'date': target_date,
    'generated_at': f'{target_date}T16:08:00',
    'strategy_A': signals,
    'count': len(signals)
}

outfile = f'signals_A_v2_{target_date}.json'
with open(outfile, 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f'[OK] {len(signals)} signals → {outfile}')
"

echo "[$(date)] Done."
