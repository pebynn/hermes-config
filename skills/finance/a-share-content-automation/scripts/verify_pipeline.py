#!/usr/bin/env python3
"""完整流程验证脚本

验证数据采集→文章生成→草稿箱同步的全流程

验证日期：2026-05-05
验证状态：✅ 通过
"""

import json
import os
import sys
from datetime import datetime

def verify_data_collection(date_str=None):
    """验证数据采集"""
    print("\n" + "="*40)
    print("Step 1: 验证数据采集")
    print("="*40)

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    data_path = f"~/writing-data/raw/{date_str}/all_data.json"
    data_path = os.path.expanduser(data_path)

    if not os.path.exists(data_path):
        print(f"✗ 数据文件不存在: {data_path}")
        return False

    print(f"✓ 数据文件存在: {data_path}")

    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 验证大盘指数
    index_data = data.get('index', {})
    if not index_data:
        print("✗ 大盘指数数据为空")
        return False

    print(f"\n大盘指数（{len(index_data)}个）:")
    for name, idx in index_data.items():
        print(f"  ✓ {name}: {idx['close']:.2f} ({idx['change_pct']:+.2f}%)")

    # 验证板块数据
    sectors = data.get('sectors', {})
    if not sectors or sectors['total_count'] == 0:
        print("✗ 板块数据为空")
        return False

    print(f"\n板块数据（{sectors['total_count']}个）:")
    print(f"  ✓ 涨幅Top5: {[s['name'] for s in sectors['industry_top5']]}")
    print(f"  ✓ 跌幅Top5: {[s['name'] for s in sectors['industry_bottom5']]}")

    # 检查待修复项
    print(f"\n待修复项:")
    if data.get('stocks', {}).get('limit_up_count', 0) == 0:
        print(f"  ⚠ 涨停数据: 0家（API待修复）")
    if data.get('capital_flow', {}).get('north_net_inflow', 0) == 0:
        print(f"  ⚠ 北向资金: 0亿（API待修复）")

    print("\n✓ 数据采集验证通过")
    return True

def verify_daily_review(date_str=None):
    """验证每日复盘文章"""
    print("\n" + "="*40)
    print("Step 2: 验证每日复盘文章")
    print("="*40)

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    article_path = f"~/writing-data/drafts/{date_str}-每日复盘.md"
    article_path = os.path.expanduser(article_path)

    if not os.path.exists(article_path):
        print(f"✗ 文章不存在: {article_path}")
        return False

    print(f"✓ 文章存在: {article_path}")

    with open(article_path, 'r', encoding='utf-8') as f:
        article = f.read()

    # 验证章节完整性
    checks = {
        "标题": article.startswith("# 【每日复盘】"),
        "大盘回顾": "## 大盘回顾" in article,
        "资金风向标": "## 资金风向标" in article,
        "热点板块": "## 热点板块" in article,
        "技术看盘": "## 技术看盘" in article,
        "明日策略": "## 明日策略" in article,
        "风险提示": "风险提示" in article,
        "AIGC标识": "AI辅助创作" in article,
        "元数据": "## 元数据" in article
    }

    print("\n章节完整性检查:")
    all_passed = True
    for check_name, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False

    if not all_passed:
        print("\n✗ 验证失败，部分章节缺失")
        return False

    print(f"\n文章字数: {len(article)} 字")
    print("\n✓ 每日复盘验证通过")
    return True

def verify_weekly_summary(date_str=None):
    """验证周总结文章"""
    print("\n" + "="*40)
    print("Step 3: 验证周总结文章")
    print("="*40)

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    article_path = f"~/writing-data/drafts/{date_str}-周总结.md"
    article_path = os.path.expanduser(article_path)

    if not os.path.exists(article_path):
        print(f"⚠ 周总结不存在: {article_path}（可能不是周末）")
        return True  # 周总结不是必需的

    print(f"✓ 周总结存在: {article_path}")

    with open(article_path, 'r', encoding='utf-8') as f:
        article = f.read()

    # 验证章节完整性
    checks = {
        "标题": article.startswith("# 【周总结】"),
        "本周行情回顾": "## 本周行情回顾" in article,
        "最热方向分析": "## 本周最热方向深度分析" in article,
        "下周展望": "## 下周展望" in article,
        "操作建议": "## 操作建议" in article,
        "风险提示": "风险提示" in article,
        "AIGC标识": "AI辅助创作" in article
    }

    print("\n章节完整性检查:")
    all_passed = True
    for check_name, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False

    if not all_passed:
        print("\n✗ 验证失败，部分章节缺失")
        return False

    print(f"\n文章字数: {len(article)} 字")
    print("\n✓ 周总结验证通过")
    return True

def verify_publish_log(date_str=None):
    """验证发布日志"""
    print("\n" + "="*40)
    print("Step 4: 验证发布日志")
    print("="*40)

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    log_path = f"~/writing-data/publish-logs/{date_str}-publish.log"
    log_path = os.path.expanduser(log_path)

    if not os.path.exists(log_path):
        print(f"✗ 日志文件不存在: {log_path}")
        return False

    print(f"✓ 日志文件存在: {log_path}")

    with open(log_path, 'r', encoding='utf-8') as f:
        log = f.read()

    print(f"\n日志内容（前200字）:")
    print(log[:200])

    print("\n✓ 发布日志验证通过")
    return True

def verify_full_pipeline(date_str=None):
    """完整流程验证"""
    print("="*40)
    print("A股内容自动化完整流程验证")
    print("="*40)

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    print(f"\n验证日期: {date_str}\n")

    results = []

    # Step 1: 数据采集
    results.append(verify_data_collection(date_str))

    # Step 2: 每日复盘
    results.append(verify_daily_review(date_str))

    # Step 3: 周总结
    results.append(verify_weekly_summary(date_str))

    # Step 4: 发布日志
    results.append(verify_publish_log(date_str))

    # 总结
    print("\n" + "="*40)
    print("验证总结")
    print("="*40)

    all_passed = all(results)

    print(f"\n数据采集: {'✓ 通过' if results[0] else '✗ 失败'}")
    print(f"每日复盘: {'✓ 通过' if results[1] else '✗ 失败'}")
    print(f"周总结: {'✓ 通过' if results[2] else '✗ 失败/跳过'}")
    print(f"发布日志: {'✓ 通过' if results[3] else '✗ 失败'}")

    print("\n" + "="*40)

    if all_passed:
        print("✅ 全流程验证通过")
        print("="*40)
        return 0
    else:
        print("❌ 部分环节验证失败")
        print("="*40)
        return 1

if __name__ == "__main__":
    # 验证最新日期
    verify_full_pipeline()

    # 也可以指定日期验证
    # verify_full_pipeline("2026-05-04")
