#!/usr/bin/env python3
"""TDD验证脚本 — 策略A优化验收测试 (预期RED→GREEN)
Run: python3 /home/pebynn/.hermes/plans/t_09735095_test.py
"""
import sys, ast, re

STRATEGY_FILE = "/home/pebynn/quant/evo_optimizer/strategy_momentum.py"
errors = []

with open(STRATEGY_FILE) as f:
    source = f.read()

# Test 1: OUTPUT_FILE = backtest_A.csv
m = re.search(r'OUTPUT_FILE\s*=\s*"([^"]+)"', source)
if m:
    outfile = m.group(1)
    if "backtest_A.csv" not in outfile:
        errors.append(f"TEST1 RED: OUTPUT_FILE={outfile}, expected backtest_A.csv")
    else:
        print(f"TEST1 GREEN: OUTPUT_FILE={outfile}")
else:
    errors.append("TEST1 RED: OUTPUT_FILE not found")

# Test 2: LEVERAGE = 1.0
m = re.search(r'LEVERAGE\s*=\s*([\d.]+)', source)
if m:
    lev = float(m.group(1))
    if lev != 1.0:
        errors.append(f"TEST2 RED: LEVERAGE={lev}, expected 1.0")
    else:
        print(f"TEST2 GREEN: LEVERAGE={lev}")
else:
    errors.append("TEST2 RED: LEVERAGE not found")

# Test 3: TOP_N in [8, 9, 10]
m = re.search(r'TOP_N\s*=\s*(\d+)', source)
if m:
    topn = int(m.group(1))
    if topn not in (8, 9, 10):
        errors.append(f"TEST3 RED: TOP_N={topn}, expected 8-10")
    else:
        print(f"TEST3 GREEN: TOP_N={topn}")
else:
    errors.append("TEST3 RED: TOP_N not found")

# Test 4: turnover_ratio in FACTOR_NAMES
if "'turnover_ratio'" in source:
    print("TEST4 GREEN: turnover_ratio found in FACTOR_NAMES")
else:
    errors.append("TEST4 RED: 'turnover_ratio' NOT in FACTOR_NAMES")

# Test 5: amount_ratio in FACTOR_NAMES
if "'amount_ratio'" in source:
    print("TEST5 GREEN: amount_ratio found in FACTOR_NAMES")
else:
    errors.append("TEST5 RED: 'amount_ratio' NOT in FACTOR_NAMES")

# Test 6: Batch TP logic (tranche or TP1 or take_profit)
if re.search(r'(tranche|TP1|take_profit|batch.*tp|tp1_hit)', source, re.I):
    print("TEST6 GREEN: Batch take-profit logic found")
else:
    errors.append("TEST6 RED: No batch take-profit logic")

# Test 7: Syntax check
import py_compile
try:
    py_compile.compile(STRATEGY_FILE, doraise=True)
    print("TEST7 GREEN: Syntax OK")
except py_compile.PyCompileError as e:
    errors.append(f"TEST7 RED: Syntax error: {e}")

print(f"\n{'='*50}")
if errors:
    print(f"FAILED {len(errors)}/{7} tests (expected RED→GREEN after implementation):")
    for e in errors:
        print(f"  ❌ {e}")
    sys.exit(1)
else:
    print("ALL 7 TESTS GREEN — Implementation complete!")
    sys.exit(0)
