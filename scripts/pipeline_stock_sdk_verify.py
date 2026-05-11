#!/usr/bin/env python3
"""pipeline_stock_sdk_verify.py — Stock-SDK 集成后早报稳定性验证"""
import subprocess, json
from pathlib import Path
from datetime import datetime
import traceback

HOME = Path.home()
# 检查最近3个交易日的采集数据完整性
raw_dir = HOME / 'writing-data' / 'raw'
charts_dir = HOME / 'writing-data' / 'charts'

# 交易日历（简化版 - 从AKShare每日数据推断）
trading_dates = sorted([d.name for d in raw_dir.iterdir() if d.is_dir() and d.name[:4].isdigit()])
recent = trading_dates[-5:] if len(trading_dates) >= 5 else trading_dates

print(f"Stock-SDK 集成验证报告")
print(f"{'='*50}")
print(f"  检查范围: 最近 {len(recent)} 个交易日")
print()

issues = []
for d in recent:
    date_issues = []
    # all_data.json是否存在
    data_file = raw_dir / d / 'all_data.json'
    if not data_file.exists():
        date_issues.append("all_data.json 缺失")
    else:
        try:
            data = json.loads(data_file.read_text())
            # 关键字段检查
            for key in ['market', 'sector_flow', 'limit_up_pool']:
                if key not in data or not data[key]:
                    date_issues.append(f"{key} 为空")
        except:
            traceback.print_exc()
            date_issues.append("all_data.json 解析失败")

    # 图表检查
    chart_pattern = list(charts_dir.glob(f'{d}*.png'))
    if len(chart_pattern) < 3:
        date_issues.append(f"图表不足 ({len(chart_pattern)}张)")

    if date_issues:
        print(f"  ⚠️ {d}: {'; '.join(date_issues)}")
        issues.append((d, date_issues))
    else:
        print(f"  ✅ {d}: 数据完整")

print()
if not issues:
    print("✅ 最近交易日数据完整，stock_sdk 集成稳定")
else:
    print(f"⚠️ {len(issues)} 天有数据问题，需排查")

# 数据源标签检查
print()
print(f"  多源降级测试:")
for d in recent:
    data_file = raw_dir / d / 'all_data.json'
    if data_file.exists():
        src_log = HOME / 'writing-data' / 'logs' / 'collect_data.log'
        if src_log.exists():
            log_lines = src_log.read_text().split('\n')
            d_lines = [l for l in log_lines if d in l and 'source' in l.lower()]
            sources = set()
            for l in d_lines[-20:]:
                if 'sina' in l.lower(): sources.add('Sina')
                if 'stock_sdk' in l.lower() or 'node' in l.lower(): sources.add('stock_sdk')
                if 'akshare' in l.lower(): sources.add('AKShare')
                if 'xueqiu' in l.lower(): sources.add('雪球')
            print(f"    {d}: 数据源={sources or '无记录'}")
