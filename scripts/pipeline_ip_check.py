#!/usr/bin/env python3
"""pipeline_ip_check.py — 2026-06-07 IP白名单评估"""
import subprocess, json
from pathlib import Path
import traceback

# 检查历史IP变更记录
LOG_FILE = Path.home() / 'writing-data' / 'logs' / 'publish_draft.log'
ip_changes = 0
current_ip = ""

if LOG_FILE.exists():
    for line in LOG_FILE.read_text().split('\n'):
        if 'new_ip' in line.lower() or 'whitelist' in line.lower() or '113.110.' in line:
            ip_changes += 1

# 获取当前公网IP
try:
    r = subprocess.run(['curl', '-s', 'https://api.ipify.org'], capture_output=True, text=True, timeout=10)
    current_ip = r.stdout.strip()
except:
    traceback.print_exc()
    current_ip = "(无法获取)"

print(f"IP白名单评估报告 ({Path.home()})")
print(f"{'='*50}")
print(f"  当前公网IP: {current_ip}")
print(f"  IP变更记录数: {ip_changes}")
print()

if ip_changes <= 1:
    print(f"  评估: ✅ IP稳定 (30天内仅{ip_changes}次变更)")
    print(f"  建议: 保留方案A，无需升级")
elif ip_changes <= 3:
    print(f"  评估: ⚠️ 偶有变更 ({ip_changes}次)")
    print(f"  建议: 保留方案A，但记录需要手动更新白名单的次数")
else:
    print(f"  评估: ❌ IP频繁变更 ({ip_changes}次)")
    print(f"  建议: 升级到方案B (SSH隧道至固定IP VPS)")
