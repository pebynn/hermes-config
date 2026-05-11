#!/usr/bin/env python3
"""Try PDD listing in dry-run mode first, then with draft mode"""
import subprocess, sys, os, json

# Step 1: Try dry run to verify listing data is correct
print("=" * 50)
print("Step 1: Dry run to verify listing data")
print("=" * 50)

result = subprocess.run(
    [sys.executable, "/home/pebynn/PDD/pdd_listing_v3.py",
     "--date", "2026-05-11",
     "--dry-run",
     "--headless", "0"],
    capture_output=True, text=True, timeout=60
)
print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-1000:])
print(f"Exit code: {result.returncode}")
