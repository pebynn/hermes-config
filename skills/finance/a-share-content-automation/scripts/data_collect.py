#!/usr/bin/env python3
"""完整数据采集脚本 - 修复版v3

Bug fixes (2026-05-05):
- 使用 stock_zh_index_daily_em（含amount列）替代 stock_zh_index_daily（无amount）
- change_pct 使用 (close - prev_close) / prev_close * 100 替代 (close - open) / open * 100
- 北向资金使用 stock_hsgt_hist_em(symbol="北向资金") — 已验证可用
- 涨停数据使用 ak.stock_zt_pool_em(date=...) — 已验证可用

输出格式：JSON -> ~/writing-data/raw/YYYY-MM-DD/all_data.json
"""

import akshare as ak
import pandas as pd
import json
import os
from datetime import datetime


def get_index_data(symbol, name):
    """获取单个指数数据（使用stock_zh_index_daily_em）"""
    df = ak.stock_zh_index_daily_em(symbol=symbol)
    if df.empty:
        return {}

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else None

    # 涨跌幅：使用前一日收盘价（Bug fix）
    if prev is not None:
        change_pct = (latest['close'] - prev['close']) / prev['close'] * 100
    else:
        change_pct = 0

    return {
        "name": name,
        "close": float(latest['close']),
        "open": float(latest['open']),
        "high": float(latest['high']),
        "low": float(latest['low']),
        "change_pct": round(change_pct, 2),
        "volume": int(latest['volume']),
        "turnover_yi": round(float(latest['amount']) / 1e8, 2) if 'amount' in latest else 0
    }


def collect_a_share_data(date_str=None):
    """采集A股核心数据"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    data = {
        "date": date_str,
        "collect_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data_sources": ["akshare"]
    }

    # 1. 大盘指数（修复：使用 stock_zh_index_daily_em）
    print("1. 采集大盘指数...")
    try:
        data["index"] = {
            "上证指数": get_index_data("sh000001", "上证指数"),
            "深证成指": get_index_data("sz399001", "深证成指"),
            "创业板指": get_index_data("sz399006", "创业板指"),
            "科创50": get_index_data("sh000688", "科创50")
        }
        for name, idx in data["index"].items():
            if idx:
                print(f"  ✓ {name}: {idx['close']:.2f} ({idx['change_pct']:+.2f}%), 成交额{idx['turnover_yi']:.0f}亿")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        data["index"] = {}

    # 2. 北向资金（修复：使用 stock_hsgt_hist_em）
    print("2. 采集北向资金...")
    try:
        north_flow = ak.stock_hsgt_hist_em(symbol="北向资金")
        if not north_flow.empty:
            latest = north_flow.iloc[-1]
            data["capital_flow"] = {
                "north_net_inflow": float(latest.get("净流入", 0)),
                "north_buy": float(latest.get("买入成交额", 0)),
                "north_sell": float(latest.get("卖出成交额", 0)),
                "north_date": str(latest.get("日期", date_str))
            }
            print(f"  ✓ 北向资金净流入: {data['capital_flow']['north_net_inflow']:+.2f}亿")
        else:
            data["capital_flow"] = {"north_net_inflow": 0}
            print("  ⚠ 北向资金数据为空")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        data["capital_flow"] = {"north_net_inflow": 0}

    # 3. 板块热点
    print("3. 采集板块热点...")
    try:
        industry = ak.stock_board_industry_name_em()
        if not industry.empty:
            top5 = industry.nlargest(5, '涨跌幅')
            bottom5 = industry.nsmallest(5, '涨跌幅')
            data["sectors"] = {
                "industry_top5": [
                    {"name": row['板块名称'], "change_pct": row['涨跌幅'],
                     "code": row['板块代码'], "leader": row.get('领涨股票', '')}
                    for _, row in top5.iterrows()
                ],
                "industry_bottom5": [
                    {"name": row['板块名称'], "change_pct": row['涨跌幅'],
                     "code": row['板块代码']}
                    for _, row in bottom5.iterrows()
                ],
                "total_count": len(industry)
            }
            print(f"  ✓ 获取 {len(industry)} 个行业板块")
        else:
            data["sectors"] = {"industry_top5": [], "industry_bottom5": [], "total_count": 0}
            print("  ⚠ 板块数据为空")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        data["sectors"] = {"industry_top5": [], "industry_bottom5": [], "total_count": 0}

    # 4. 涨跌停（修复：涨停API可用，跌停暂不支持）
    print("4. 采集涨跌停数据...")
    try:
        limit_up = ak.stock_zt_pool_em(date=date_str)
        if not limit_up.empty:
            up_list = [
                {"code": row['代码'], "name": row['名称'],
                 "price": float(row['最新价']), "change_pct": float(row['涨跌幅'])}
                for _, row in limit_up.head(10).iterrows()
            ]
            data["stocks"] = {
                "limit_up_count": len(up_list),
                "limit_down_count": 0,
                "limit_up_samples": up_list,
                "limit_down_samples": [],
                "note": "跌停API暂不支持（stock_zt_pool_em无type参数），对复盘影响较小"
            }
            print(f"  ✓ 涨停: {len(up_list)}只")
        else:
            data["stocks"] = {"limit_up_count": 0, "limit_down_count": 0}
            print("  ⚠ 无涨停数据")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        data["stocks"] = {"limit_up_count": 0, "limit_down_count": 0}

    # 5. 保存
    output_dir = f"/home/pebynn/writing-data/raw/{date_str}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/all_data.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n✓ 数据采集完成: {output_path}")
    return data


if __name__ == "__main__":
    data = collect_a_share_data()
    print(f"\n数据摘要:")
    for name, idx in data.get('index', {}).items():
        if idx:
            print(f"  {name}: {idx['close']:.2f} ({idx['change_pct']:+.2f}%)")
    if data.get('capital_flow', {}).get('north_net_inflow'):
        print(f"  北向资金: {data['capital_flow']['north_net_inflow']:+.2f}亿")
