#!/usr/bin/env python3
"""
电商每日运营日报数据采集脚本
读取 PDD 运营数据目录，输出结构化 JSON 报告到 stdout。

数据目录:
  - ~/PDD/运营/orders/{日期}.json
  - ~/PDD/运营/returns/{日期}.json
  - ~/PDD/运营/reviews/{日期}.json
  - ~/PDD/运营/inventory/current.json
  - ~/PDD/商品/{日期}/  (各店铺子目录)

用法:
  python daily_ops_report.py              # 采集当天数据
  python daily_ops_report.py 2026-04-28   # 采集指定日期数据
"""

import json
import os
import sys
from collections import Counter
from datetime import date, datetime

# ── 路径常量 ──────────────────────────────────────────────
HOME = os.path.expanduser("~")
BASE_OP = os.path.join(HOME, "PDD", "运营")
BASE_PROD = os.path.join(HOME, "PDD", "商品")

# ── 日期处理 ──────────────────────────────────────────────
def get_report_date() -> str:
    """获取报告日期。支持命令行参数传入，默认当天。"""
    if len(sys.argv) > 1:
        raw = sys.argv[1].strip()
        # 验证日期格式
        datetime.strptime(raw, "%Y-%m-%d")
        return raw
    return date.today().isoformat()


# ── 数据读取工具 ──────────────────────────────────────────
def load_json(path: str):
    """安全读取 JSON 文件，不存在或异常返回 None。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
        print(f"[WARN] 跳过文件 {path}: {e}", file=sys.stderr)
        return None


# ── 订单概况 ──────────────────────────────────────────────
def build_order_summary(orders: list) -> dict:
    """统计订单概况，单位从分转元。"""
    if not orders:
        return {
            "总订单数": 0,
            "总金额": 0,
            "待发货": 0,
            "已发货": 0,
            "已完成": 0,
        }

    total_orders = len(orders)
    total_amount = sum(o.get("total", 0) for o in orders)
    pending = sum(1 for o in orders if o.get("status") == "pending")
    shipped = sum(1 for o in orders if o.get("status") == "shipped")
    completed = sum(1 for o in orders if o.get("status") == "completed")

    return {
        "总订单数": total_orders,
        "总金额": round(total_amount / 100, 2),
        "待发货": pending,
        "已发货": shipped,
        "已完成": completed,
    }


# ── 退货概况 ──────────────────────────────────────────────
def build_return_summary(returns: list, total_orders: int) -> dict:
    """统计退货概况，找出主要原因。"""
    if not returns:
        return {
            "退货数": 0,
            "退货率": 0,
            "退货总额": 0,
            "主要原因": "无",
        }

    return_count = len(returns)
    return_rate = round(return_count / total_orders, 4) if total_orders > 0 else 0
    return_amount = sum(r.get("amount", 0) for r in returns)

    # 统计退货原因
    reasons = [r.get("reason", "其他") for r in returns if r.get("reason")]
    main_reason = Counter(reasons).most_common(1)[0][0] if reasons else "其他"

    return {
        "退货数": return_count,
        "退货率": return_rate,
        "退货总额": round(return_amount / 100, 2),
        "主要原因": main_reason,
    }


# ── 评价概况 ──────────────────────────────────────────────
def build_review_summary(reviews: list) -> dict:
    """统计评价概况。"""
    if not reviews:
        return {
            "总评价数": 0,
            "平均评分": 0,
            "差评数": 0,
            "待回复": 0,
        }

    total = len(reviews)
    ratings = [r.get("rating", 0) for r in reviews]
    avg_rating = round(sum(ratings) / total, 2) if total > 0 else 0
    negative_count = sum(1 for r in reviews if r.get("is_negative"))
    unreplied = sum(1 for r in reviews if r.get("reply") is None or r.get("reply") == "")

    return {
        "总评价数": total,
        "平均评分": avg_rating,
        "差评数": negative_count,
        "待回复": unreplied,
    }


# ── 库存预警 ──────────────────────────────────────────────
def build_inventory_alerts(inventory: list) -> list:
    """提取库存预警商品：low_stock_warning 为 true 或 库存 <= reorder_point。"""
    if not inventory:
        return []

    alerts = []
    for item in inventory:
        stock = item.get("total_stock", 0)
        reorder = item.get("reorder_point", 0)
        warning = item.get("low_stock_warning", False)

        if warning or (reorder > 0 and stock <= reorder):
            alerts.append({
                "商品": item.get("goods_name", ""),
                "SKU": item.get("sku_spec", ""),
                "库存": stock,
                "建议补货": True,
            })

    return alerts


# ── 今日上新 ──────────────────────────────────────────────
def build_new_listings(report_date: str) -> list:
    """扫描 ~/PDD/商品/{日期}/ 下各子目录，收集今日上新产品。"""
    prod_dir = os.path.join(BASE_PROD, report_date)
    if not os.path.isdir(prod_dir):
        return []

    listings = []
    for shop_dir in sorted(os.listdir(prod_dir)):
        shop_path = os.path.join(prod_dir, shop_dir)
        if not os.path.isdir(shop_path):
            continue

        # 读取店铺信息
        shop_info_path = os.path.join(shop_path, "_店铺信息.json")
        shop_info = load_json(shop_info_path)
        shop_name = (shop_info.get("shop_name") or shop_dir.split("-")[0]) if shop_info else shop_dir.split("-")[0]

        # 读取 listing
        listing_path = os.path.join(shop_path, "listing-ready", "listing.json")
        listing = load_json(listing_path)
        if not listing:
            continue

        goods_name = listing.get("goods_name", "未知商品")
        sku_count = len(listing.get("sku_list", []))
        # listing 中 goods_number 是总库存，sku_list 数量 = 件数(SPU数)
        items_count = 1  # 每个 listing 对应一个 SPU（商品）

        listings.append({
            "商品": goods_name,
            "店铺": shop_name,
            "件数": items_count,
        })

    return listings


# ── 销售排行 TOP3 ─────────────────────────────────────────
def build_sales_top3(orders: list) -> list:
    """按商品名称聚合销量和金额，取 TOP3。"""
    if not orders:
        return []

    # 按 goods_name 聚合
    sales_map = {}
    for o in orders:
        name = o.get("goods_name", "未知商品")
        qty = o.get("quantity", 0)
        amt = o.get("total", 0)
        if name in sales_map:
            sales_map[name]["销量"] += qty
            sales_map[name]["金额"] += amt
        else:
            sales_map[name] = {"销量": qty, "金额": amt}

    # 按销量降序排列
    sorted_items = sorted(sales_map.items(), key=lambda x: -x[1]["销量"])

    top3 = []
    for name, data in sorted_items[:3]:
        top3.append({
            "商品": name,
            "销量": data["销量"],
            "金额": round(data["金额"] / 100, 2),
        })

    return top3


# ── 主流程 ────────────────────────────────────────────────
def main():
    report_date = get_report_date()

    # 读订单
    orders_path = os.path.join(BASE_OP, "orders", f"{report_date}.json")
    orders = load_json(orders_path) or []

    # 读退货
    returns_path = os.path.join(BASE_OP, "returns", f"{report_date}.json")
    returns = load_json(returns_path) or []

    # 读评价
    reviews_path = os.path.join(BASE_OP, "reviews", f"{report_date}.json")
    reviews = load_json(reviews_path) or []

    # 读库存
    inventory_path = os.path.join(BASE_OP, "inventory", "current.json")
    inventory = load_json(inventory_path) or []

    # 组装报告
    report = {
        "日期": report_date,
        "订单概况": build_order_summary(orders),
        "退货概况": build_return_summary(returns, len(orders)),
        "评价概况": build_review_summary(reviews),
        "库存预警": build_inventory_alerts(inventory),
        "今日上新": build_new_listings(report_date),
        "销售排行TOP3": build_sales_top3(orders),
    }

    # 输出 JSON
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
