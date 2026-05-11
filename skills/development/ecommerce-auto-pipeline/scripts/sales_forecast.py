#!/usr/bin/env python3
"""
sales_forecast.py — 基于历史订单数据的销量预测 + 库存建议

读取 ~/PDD/运营/orders/{日期}.json，输出 JSON 分析报告。

Usage:
    python sales_forecast.py
    python sales_forecast.py --days 30
    python sales_forecast.py --days 30 --date 2026-04-29
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

ORDERS_DIR = os.path.expanduser("~/PDD/运营/orders")
INVENTORY_FILE = os.path.expanduser("~/PDD/运营/inventory/current.json")
DATE_FORMAT = "%Y-%m-%d"


def load_json(path):
    """Load JSON from file, return None if missing or broken."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  [warn] 跳过 {path}: {e}", file=sys.stderr)
        return None


def parse_date_from_filename(filename):
    """Extract YYYY-MM-DD from a filename like '2026-04-29.json'."""
    stem = filename.replace(".json", "")
    try:
        return datetime.strptime(stem, DATE_FORMAT).date()
    except ValueError:
        return None


def daily_sales_trend(daily_orders):
    """Build a list of {date, orders, total} sorted by date."""
    days = sorted(daily_orders.keys())
    trend = []
    for d in days:
        items = daily_orders[d]
        total_orders = sum(item["quantity"] for item in items)
        total_amount = sum(item["total"] for item in items) / 100.0  # 分 → 元
        trend.append({
            "date": d.isoformat(),
            "orders": total_orders,
            "amount": round(total_amount, 2),
        })
    return trend


def compute_trend(daily_orders, ref_date=None):
    """
    Compare last-7-day avg order count vs the 7 days before that.
    Returns "上升", "下降", or "平稳".
    """
    days = sorted(daily_orders.keys())
    if len(days) < 14:
        return "平稳"

    recent_7 = days[-7:]
    prev_7 = days[-14:-7]

    def avg_orders(day_list):
        total = sum(
            sum(item["quantity"] for item in daily_orders[d])
            for d in day_list
        )
        return total / len(day_list)

    r_avg = avg_orders(recent_7)
    p_avg = avg_orders(prev_7)

    if p_avg == 0:
        return "上升" if r_avg > 0 else "平稳"

    ratio = r_avg / p_avg
    if ratio > 1.15:
        return "上升"
    elif ratio < 0.85:
        return "下降"
    return "平稳"


def moving_average_forecast(daily_orders, window=3):
    """
    3-day moving average for the last `window` days with data.
    Returns forecasted order count and amount (元).
    """
    days = sorted(daily_orders.keys())
    if len(days) < window:
        window = len(days)
    if window == 0:
        return {"预计订单": 0, "预计金额": 0.0}

    recent = days[-window:]
    total_orders = 0
    total_amount_fen = 0
    for d in recent:
        items = daily_orders[d]
        total_orders += sum(item["quantity"] for item in items)
        total_amount_fen += sum(item["total"] for item in items)

    avg_orders = total_orders / window
    avg_amount = total_amount_fen / window / 100.0
    return {
        "预计订单": round(avg_orders, 1),
        "预计金额": round(avg_amount, 2),
    }


def product_ranking(daily_orders, lookback_days=7, ref_date=None):
    """Rank products by sales volume in the last N days."""
    if ref_date is None:
        ref_date = date.today()
    cutoff = ref_date - timedelta(days=lookback_days)
    product_data = defaultdict(lambda: {"quantity": 0, "total_fen": 0})

    total_qty = 0
    for d, items in daily_orders.items():
        if d < cutoff:
            continue
        for item in items:
            name = item["goods_name"]
            product_data[name]["quantity"] += item["quantity"]
            product_data[name]["total_fen"] += item["total"]
            total_qty += item["quantity"]

    ranking = []
    for name, data in product_data.items():
        amount = data["total_fen"] / 100.0
        pct = f"{data['quantity'] / total_qty * 100:.1f}%" if total_qty else "0.0%"
        ranking.append({
            "商品": name,
            "销量": data["quantity"],
            "金额": round(amount, 2),
            "占比": pct,
        })

    ranking.sort(key=lambda x: x["销量"], reverse=True)
    return ranking


def load_inventory_map():
    """Load inventory and build {goods_name: total_stock}. Groups SKUs under the same goods_name."""
    data = load_json(INVENTORY_FILE)
    if data is None:
        return {}
    inv = defaultdict(int)
    for entry in data:
        name = entry.get("goods_name", "")
        stock = entry.get("total_stock", 0)
        inv[name] += stock
    return dict(inv)


def inventory_suggestions(product_ranking_7d, inv_map):
    """
    Build inventory suggestions based on average daily sales (7d) and current stock.
    """
    if not product_ranking_7d:
        return []

    suggestions = []
    for p in product_ranking_7d:
        name = p["商品"]
        qty_7d = p["销量"]
        daily_avg = qty_7d / 7.0
        stock = inv_map.get(name, 0)

        days_available = round(stock / daily_avg, 1) if daily_avg > 0 else float("inf")
        should_reorder = daily_avg > 0 and (stock / daily_avg if daily_avg > 0 else float("inf")) < 30

        suggestions.append({
            "商品": name,
            "日均销量": round(daily_avg, 1),
            "当前库存": stock,
            "预计可用天数": days_available if days_available != float("inf") else "充足",
            "建议补货": should_reorder,
        })

    return suggestions


def collect_orders(lookback_days):
    """Scan ORDERS_DIR for JSON files within lookback window, return daily_orders dict."""
    daily_orders = defaultdict(list)
    today = date.today()

    if not os.path.isdir(ORDERS_DIR):
        print(f"[error] 订单目录不存在: {ORDERS_DIR}", file=sys.stderr)
        sys.exit(1)

    for fname in sorted(os.listdir(ORDERS_DIR)):
        if not fname.endswith(".json"):
            continue
        order_date = parse_date_from_filename(fname)
        if order_date is None:
            continue
        if (today - order_date).days > lookback_days:
            continue
        if order_date > today:
            continue  # skip future dates

        path = os.path.join(ORDERS_DIR, fname)
        data = load_json(path)
        if data is None:
            continue
        if not isinstance(data, list):
            continue
        daily_orders[order_date].extend(data)

    return daily_orders


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="订单销量预测与库存建议")
    parser.add_argument("--days", type=int, default=30, help="扫描近N天的订单文件 (默认 30)")
    parser.add_argument("--date", type=str, default=None,
                        help="基准日期 YYYY-MM-DD (默认今天)")
    args = parser.parse_args()

    if args.date:
        try:
            ref_date = datetime.strptime(args.date, DATE_FORMAT).date()
        except ValueError:
            print(f"[error] 无效日期格式: {args.date}", file=sys.stderr)
            sys.exit(1)
    else:
        ref_date = date.today()

    daily_orders = collect_orders(args.days)

    if not daily_orders:
        report = {
            "日期": ref_date.isoformat(),
            "数据范围": f"{(ref_date - timedelta(days=args.days)).isoformat()} ~ {ref_date.isoformat()}",
            "总订单": 0,
            "总金额": 0.0,
            "日均订单": 0.0,
            "日均金额": 0.0,
            "趋势": "平稳",
            "商品排行": [],
            "明日预测": {"预计订单": 0, "预计金额": 0.0},
            "库存建议": [],
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(0)

    # --- Aggregate totals ---
    total_orders = 0
    total_amount_fen = 0
    for items in daily_orders.values():
        for item in items:
            total_orders += item["quantity"]
            total_amount_fen += item["total"]

    num_days = len(daily_orders)
    total_amount_yuan = total_amount_fen / 100.0
    avg_daily_orders = round(total_orders / num_days, 1) if num_days else 0.0
    avg_daily_amount = round(total_amount_yuan / num_days, 1) if num_days else 0.0

    # --- Trend ---
    trend = compute_trend(daily_orders)

    # --- Daily trend (full series) ---
    trend_series = daily_sales_trend(daily_orders)

    # --- Product ranking (last 7 days) ---
    ranking_7d = product_ranking(daily_orders, lookback_days=7, ref_date=ref_date)

    # --- 3-day moving average forecast ---
    forecast = moving_average_forecast(daily_orders, window=3)

    # --- Inventory ---
    inv_map = load_inventory_map()
    inv_suggestions = inventory_suggestions(ranking_7d, inv_map)

    # --- Date range string ---
    all_dates = sorted(daily_orders.keys())
    date_range = f"{all_dates[0].isoformat()} ~ {all_dates[-1].isoformat()}"

    # --- Build report ---
    report = {
        "日期": ref_date.isoformat(),
        "数据范围": date_range,
        "总订单": total_orders,
        "总金额": round(total_amount_yuan, 2),
        "日均订单": avg_daily_orders,
        "日均金额": avg_daily_amount,
        "趋势": trend,
        "每日销量": trend_series,
        "商品排行": ranking_7d,
        "明日预测": forecast,
        "库存建议": inv_suggestions,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))
