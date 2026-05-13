#!/usr/bin/env python3
"""Quick test - verify daily_kline_update.py can run with --help for basic validation."""
import subprocess, sys
result = subprocess.run(
    ['/home/pebynn/tools/quant_env/bin/python3', '/home/pebynn/quant/daily_kline_update.py', '--help'],
    capture_output=True, text=True, timeout=15, env={'HOME': '/home/pebynn', 'PATH': '/home/pebynn/tools/quant_env/bin:/usr/local/bin:/usr/bin:/bin'}
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("RC:", result.returncode)
