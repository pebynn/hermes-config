#!/bin/bash
# Wrapper for daily K线更新 — delegates to standalone Python script
# Retry up to 3 times on failure (handles transient Tushare 401)
exec /home/pebynn/tools/quant_env/bin/python3 /home/pebynn/quant/daily_kline_update.py "$@"
