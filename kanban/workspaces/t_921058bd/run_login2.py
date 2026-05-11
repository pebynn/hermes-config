#!/usr/bin/env python3
"""Run PDD login with headless=False, capture screenshot on failure"""
import subprocess, sys, os, json

result = subprocess.run(
    [sys.executable, "/home/pebynn/PDD/pdd_login_v2.py"],
    capture_output=True, text=True, timeout=200
)
print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-2000:])
print(f"Exit code: {result.returncode}")

auth_path = os.path.expanduser("~/.pdd_auth.json")
if os.path.exists(auth_path):
    size = os.path.getsize(auth_path)
    print(f"\nAuth file: {auth_path} ({size} bytes) - CREATED")
    with open(auth_path) as f:
        data = json.load(f)
    print(f"Cookies: {len(data.get('cookies', []))}")
    print(f"Origins: {len(data.get('origins', []))}")
else:
    print(f"\nAuth file NOT created")
    # Check for screenshot
    ss = os.path.expanduser("~/PDD/slider_debug.png")
    if os.path.exists(ss):
        print(f"Screenshot saved: {ss} ({os.path.getsize(ss)} bytes)")
