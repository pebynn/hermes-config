#!/usr/bin/env python3
"""
5_dashboard.py — 运营看板

汇总订单/退货/评价/库存数据，输出运营概览报告。

用法：
    # 查看当日看板
    python 5_dashboard.py

    # 指定日期
    python 5_dashboard.py --date 2026-04-27

    # 近7日汇总
    python 5_dashboard.py --days 7

数据目录: ~/PDD/运营/ → orders, returns, reviews, inventory
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta

OPS_ROOT = os.path.expanduser("~/PDD/运营")
ORDERS_DIR = os.path.join(OPS_ROOT, "orders")
RETURNS_DIR = os.path.join(OPS_ROOT, "returns")
REVIEWS_DIR = os.path.join(OPS_ROOT, "reviews")
INVENTORY_DIR = os.path.join(OPS_ROOT, "inventory")
INVENTORY_FILE = os.path.join(INVENTORY_DIR, "current.json")


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "STEP": "📌"}.get(level, "•")
    print(f"  {icon} [{ts}] {msg}")


def load_json_file(fpath: str) -> list:
    if os.path.isfile(fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def collect_data(date_str: str) -> dict:
    """收集指定日期的运营数据"""
    orders_file = os.path.join(ORDERS_DIR, f"{date_str}.json")
    returns_file = os.path.join(RETURNS_DIR, f"{date_str}.json")
    reviews_file = os.path.join(REVIEWS_DIR, f"{date_str}.json")

    orders = load_json_file(orders_file)
    returns = load_json_file(returns_file)
    reviews = load_json_file(reviews_file)
    inventory = load_json_file(INVENTORY_FILE)

    # 订单统计
    total_orders = len(orders)
    pending_orders = sum(1 for o in orders if o.get("status") == "pending")
    shipped_orders = sum(1 for o in orders if o.get("status") == "shipped")
    completed_orders = sum(1 for o in orders if o.get("status") == "completed")
    total_revenue = sum(o.get("total", 0) for o in orders) / 100
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

    # 退货统计
    total_returns = len(returns)
    pending_returns = sum(1 for r in returns if r.get("status") == "pending")
    approved_returns = sum(1 for r in returns if r.get("status") == "approved")
    refunded_returns = sum(1 for r in returns if r.get("status") == "refunded")
    total_refund_amount = sum(r.get("amount", 0) for r in returns if r.get("status") == "refunded") / 100

    # 评价统计
    total_reviews = len(reviews)
    negative_reviews = sum(1 for r in reviews if r.get("is_negative"))
    unreplied_negative = sum(1 for r in reviews if r.get("is_negative") and r.get("reply") is None)
    avg_rating = sum(r.get("rating", 5) for r in reviews) / total_reviews if total_reviews > 0 else 0

    # 库存预警
    low_stock_count = sum(1 for i in inventory if i.get("low_stock_warning"))
    out_of_stock_count = sum(1 for i in inventory if i.get("total_stock", 0) <= 0)

    return {
        "date": date_str,
        "orders": {
            "total": total_orders,
            "pending": pending_orders,
            "shipped": shipped_orders,
            "completed": completed_orders,
            "revenue": total_revenue,
            "avg_order": avg_order_value,
        },
        "returns": {
            "total": total_returns,
            "pending": pending_returns,
            "approved": approved_returns,
            "refunded": refunded_returns,
            "refund_amount": total_refund_amount,
        },
        "reviews": {
            "total": total_reviews,
            "negative": negative_reviews,
            "unreplied_negative": unreplied_negative,
            "avg_rating": avg_rating,
        },
        "inventory": {
            "total_sku": len(inventory),
            "low_stock": low_stock_count,
            "out_of_stock": out_of_stock_count,
        },
    }


def print_divider(char="=", width=55):
    print(f"  {char * width}")


def print_kpi(label: str, value, unit: str = "", width: int = 25):
    print(f"    {label:<{width}s} {value}{unit}")


def show_dashboard(data: dict, is_multi_day: bool = False):
    """显示运营看板"""
    d = data
    o = d["orders"]
    r = d["returns"]
    rv = d["reviews"]
    inv = d["inventory"]

    print()
    print_divider()
    print(f"  📊 运营看板 — {d['date']}")
    print_divider()

    # ── 订单区 ──
    print(f"\n  📦 订单")
    print_divider("-")
    print_kpi("订单总数", o["total"])
    print_kpi("待处理", o["pending"])
    print_kpi("待发货", "──" if o["pending"] == 0 and o["total"] > 0 else o["pending"])
    print_kpi("已发货/完成", f"{o['shipped']} / {o['completed']}")
    print_kpi("总营收", f"¥{o['revenue']:.2f}")
    print_kpi("客单价", f"¥{o['avg_order']:.2f}")

    # ── 退货区 ──
    print(f"\n  ↩️  退货退款")
    print_divider("-")
    print_kpi("退货申请", r["total"])
    print_kpi("待审核", r["pending"])
    print_kpi("已批准", r["approved"])
    print_kpi("已退款", r["refunded"])
    print_kpi("退款金额", f"¥{r['refund_amount']:.2f}")
    if o["total"] > 0:
        print_kpi("退货率", f"{r['total'] / o['total'] * 100:.1f}", "%")

    # ── 评价区 ──
    print(f"\n  ⭐ 评价")
    print_divider("-")
    print_kpi("评价总数", rv["total"])
    print_kpi("差评数", rv["negative"])
    print_kpi("未回复差评", rv["unreplied_negative"])
    print_kpi("平均评分", f"{rv['avg_rating']:.1f}")
    if rv["total"] > 0:
        print_kpi("差评率", f"{rv['negative'] / rv['total'] * 100:.1f}", "%")

    # ── 库存区 ──
    print(f"\n  📦 库存")
    print_divider("-")
    print_kpi("总SKU", inv["total_sku"])
    print_kpi("低库存预警", inv["low_stock"])
    print_kpi("缺货", inv["out_of_stock"])

    # ── 健康度评分 ──
    print()
    print_divider()
    score = 100
    warnings = []

    if inv["low_stock"] > 0:
        score -= inv["low_stock"] * 5
        warnings.append(f"库存预警: {inv['low_stock']} SKU")

    if rv["unreplied_negative"] > 0:
        score -= rv["unreplied_negative"] * 3
        warnings.append(f"未回复差评: {rv['unreplied_negative']} 条")

    if r["pending"] > 3:
        score -= 5
        warnings.append(f"退货积压: {r['pending']} 条待审核")

    if o["pending"] > 10:
        score -= 5
        warnings.append(f"订单积压: {o['pending']} 条待处理")

    score = max(score, 0)
    score_icon = "🟢" if score >= 80 else ("🟡" if score >= 50 else "🔴")
    print(f"  健康度: {score_icon} {score}/100")
    if warnings:
        print(f"  待处理:")
        for w in warnings[:5]:
            print(f"    ⚠️ {w}")
    print_divider()


def main():
    parser = argparse.ArgumentParser(
        description="运营看板 — 订单/退货/评价/库存汇总",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--date", "-d", type=str, help="日期 YYYY-MM-DD，默认今天")
    parser.add_argument("--days", type=int, default=1, help="汇总天数（默认1天）")

    args = parser.parse_args()
    today = datetime.now()
    date_str = args.date or today.strftime("%Y-%m-%d")

    try:
        base_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        log(f"日期格式错误: {date_str}，使用 YYYY-MM-DD", "ERR")
        sys.exit(1)

    if args.days > 1:
        # 多日汇总
        combined = None
        for i in range(args.days):
            d = (base_date - timedelta(days=i)).strftime("%Y-%m-%d")
            data = collect_data(d)
            if combined is None:
                combined = data
                combined["date"] = f"{d} ~ {base_date.strftime('%Y-%m-%d')}"
            else:
                for section in ["orders", "returns", "reviews"]:
                    for k, v in combined[section].items():
                        if k not in ("avg_rating", "avg_order"):
                            combined[section][k] += data[section].get(k, 0)
                        elif k == "avg_rating":
                            # 加权平均
                            combined[section][k] = (
                                combined[section][k] * (i) + data[section][k]
                            ) / (i + 1) if i > 0 else data[section][k]
                combined["inventory"] = data["inventory"]  # 取最新一天
        show_dashboard(combined, is_multi_day=True)
    else:
        data = collect_data(date_str)
        show_dashboard(data)

    # 检查是否有已过期的待处理项
    print(f"\n  💡 Tip: orchestrator.py --stage ops 一键运行所有运营模块")


if __name__ == "__main__":
    main()
