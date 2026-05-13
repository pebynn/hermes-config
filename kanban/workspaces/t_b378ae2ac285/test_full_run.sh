#!/bin/bash
# Integration test: run the actual wrapper and time it
export HOME=/home/pebynn
export PATH="/home/pebynn/tools/quant_env/bin:/usr/local/bin:/usr/bin:/bin"
cd /home/pebynn/quant
echo "[$(date +%H:%M:%S)] Starting daily K-line update test..."
timeout 120 /home/pebynn/tools/quant_env/bin/python3 /home/pebynn/quant/daily_kline_update.py 2>&1 | tail -30
echo "[$(date +%H:%M:%S)] Done"
echo "Exit code: $?"
