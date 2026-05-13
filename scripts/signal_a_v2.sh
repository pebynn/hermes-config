#!/bin/bash
# 策略A v2 每日信号 — signal_a_v2.sh
# 调用 signal_generator.py (中盘50-500亿 + 模拟交易)
# Cron: 8 16 * * 1-5

set -euo pipefail
cd /home/pebynn/quant/strategies/strategy_a_momentum
exec /home/pebynn/tools/quant_env/bin/python3 signal_generator.py --variant midcap
