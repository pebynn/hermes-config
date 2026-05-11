#!/usr/bin/env python3
"""Run PDD login to generate auth file"""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "/home/pebynn/PDD/pdd_login_v2.py"],
    capture_output=True, text=True, timeout=180
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[:500])
print(f"Exit code: {result.returncode}")

# Check if auth file was created
import os
auth_path = os.path.expanduser("~/.pdd_auth.json")
if os.path.exists(auth_path):
    print(f"\nAuth file created: {auth_path} ({os.path.getsize(auth_path)} bytes)")
else:
    print(f"\nAuth file NOT created: {auth_path}")
