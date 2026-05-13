#!/home/pebynn/tools/quant_env/bin/python3
# -*- coding: utf-8 -*-
"""
策略A v2: 主力资金动量增强 — 优化版
=====================================
改进:
  1. 止损 5%→8% — 降低硬止损触发率
  2. 移动止盈 — 从高点回撤>8%止盈
  3. 动态IC权重 — 20日滚动IC调整因子权重
  4. 波动率因子 — 低波动优先，过滤假突破
"""
import sys, os, time, argparse, warnings, json
import numpy as np
import pandas as pd
from datetime import timedelta
from pathlib import Path
warnings.filterwarnings("ignore")

_QDIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..",".."))
sys.path.insert(0, _QDIR)
from data_common import _get_db_engine

# ── Config ──
START_DATE = os.environ.get("BT_START", "2021-01-01")
END_DATE   = os.environ.get("BT_END", "2025-12-31")
WARMUP_DAYS = 120
TOP_N_V2 = 10
STOP_LOSS_V2 = 0.10
TRAILING_STOP = 0.06
PORTFOLIO_STOP_V2 = 0.15
JAN_APR_EMPTY_V2 = False
MOM_ENTRY_THRESHOLD = 0.02
MIN_AMOUNT_V2 = 5e7
MIN_DAYS_V2 = 60
LEVERAGE_V2 = 1.0
TC_COST_V2 = 0.001
IC_WINDOW = 20
IC_TEMPERATURE = 2.0
VOL_WEIGHT_DEFAULT = 0.15
OUTPUT_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "output_v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_JSON = OUTPUT_DIR / "backtest_results.json"


# ═══════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════