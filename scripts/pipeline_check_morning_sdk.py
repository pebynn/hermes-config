#!/usr/bin/env python3
"""pipeline_check_morning_sdk.py — 检查morning_brief是否适配stock_sdk"""
import re
from pathlib import Path

content = Path('/home/pebynn/writing-data/scripts/morning_brief.py').read_text()
has_sdk = bool(re.search(r'stock_sdk|Node\.js|node[\s_+]', content, re.IGNORECASE))

if has_sdk:
    print("✅ morning_brief.py 已适配 stock_sdk")
else:
    print("⚠️ morning_brief.py 未适配 stock_sdk — 需要改造")
    # 找出当前数据源
    sources = set()
    for line in content.split('\n'):
        if 'akshare' in line.lower() or 'ak.' in line:
            sources.add('AKShare')
        if 'sina' in line.lower():
            sources.add('Sina')
        if 'xueqiu' in line.lower():
            sources.add('雪球')
        if 'eastmoney' in line.lower() or 'push2' in line.lower():
            sources.add('东方财富')
    print(f"   当前数据源: {sources or '未知'}")
