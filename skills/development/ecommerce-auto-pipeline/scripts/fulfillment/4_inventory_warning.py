#!/usr/bin/env python3
"""
4_inventory_warning.py — 库存预警

支持：
- 库存快照生成/更新
- 销量统计（当日/7日）
- 低库存预警检测
- 补货提醒生成

用法：
    # 初始化/更新库存（从 listing-ready/ 数据导入）
    python 4_inventory_warning.py --init

    # 录入手动库存调整
    python 4_inventory_warning.py --update --sku "黑色,XL" --stock 150

    # 库存预警检查
    python 4_inventory_warning.py --check

    # 生成补货建议
    python 4_inventory_warning.py --reorder

数据目录: ~/PDD/运营/inventory/current.json
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta

OPS_ROOT = os.path.expanduser("~/PDD/运营")
INVENTORY_DIR = os.path.join(OPS_ROOT, "inventory")
INVENTORY_FILE = os.path.join(INVENTORY_DIR, "current.json")

# 订单数据的目录路径（用于从订单推算销量）
ORDERS_DIR = os.path.join(OPS_ROOT, "orders")
PDD_GOODS_ROOT = os.path.expanduser("~/PDD/商品")

# 默认库存参数
DEFAULT_STOCK = 200
REORDER_POINT = 20


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "STEP": "📌"}.get(level, "•")
    print(f"  {icon} [{ts}] {msg}")


def ensure_dirs():
    os.makedirs(INVENTORY_DIR, exist_ok=True)


def load_inventory() -> list:
    if os.path.isfile(INVENTORY_FILE):
        with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_inventory(inventory: list):
    with open(INVENTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2)


def find_listing_jsons() -> list:
    """从 PDD商品/ 下找到所有 listing.json 来初始化库存"""
    results = []
    if not os.path.isdir(PDD_GOODS_ROOT):
        return results
    for date_dir in sorted(os.listdir(PDD_GOODS_ROOT)):
        day_path = os.path.join(PDD_GOODS_ROOT, date_dir)
        if not os.path.isdir(day_path):
            continue
        for root, dirs, files in os.walk(day_path):
            if "listing-ready" in dirs:
                lf = os.path.join(root, "listing-ready", "listing.json")
                if os.path.isfile(lf):
                    try:
                        with open(lf, "r", encoding="utf-8") as f:
                            listing = json.load(f)
                        results.append(listing)
                    except Exception:
                        pass
                dirs.remove("listing-ready")
    return results


def load_recent_orders(days: int = 7) -> list:
    """加载最近几天的订单"""
    orders = []
    if not os.path.isdir(ORDERS_DIR):
        return orders
    cutoff = datetime.now() - timedelta(days=days)
    for fname in sorted(os.listdir(ORDERS_DIR)):
        if fname.endswith(".json"):
            date_str = fname.replace(".json", "")
            try:
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue
            if file_date >= cutoff:
                fpath = os.path.join(ORDERS_DIR, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    try:
                        orders.extend(json.load(f))
                    except Exception:
                        pass
    return orders


def cmd_init():
    """从 listing-ready/ 初始化库存"""
    ensure_dirs()
    listings = find_listing_jsons()
    if not listings:
        log("未找到任何 listing.json，尝试使用空库存", "WARN")

    inventory = {}
    for l in listings:
        goods_name = l.get("goods_name", "?")
        for sku in l.get("sku_list", []):
            spec = sku.get("spec", "均码")
            key = f"{goods_name}|{spec}"
            if key not in inventory:
                inventory[key] = {
                    "goods_name": goods_name,
                    "sku_spec": spec,
                    "total_stock": DEFAULT_STOCK,
                    "sold_today": 0,
                    "sold_7d": 0,
                    "low_stock_warning": False,
                    "reorder_point": REORDER_POINT,
                    "last_updated": datetime.now().isoformat(),
                }

    # 加载近期订单推算销量
    recent_orders = load_recent_orders(7)
    today = datetime.now().strftime("%Y-%m-%d")
    for o in recent_orders:
        goods_name = o.get("goods_name", "")
        sku_spec = o.get("sku_spec", "均码")
        key = f"{goods_name}|{sku_spec}"
        qty = o.get("quantity", 1)
        if key in inventory:
            inventory[key]["sold_7d"] += qty
            if o.get("create_time", "").startswith(today):
                inventory[key]["sold_today"] += qty

    # 检查低库存
    for item in inventory.values():
        item["low_stock_warning"] = item["total_stock"] < item["reorder_point"]

    inventory_list = sorted(inventory.values(), key=lambda x: x["goods_name"])
    save_inventory(inventory_list)
    log(f"库存初始化完成: {len(inventory_list)} SKU", "OK")


def cmd_update(sku_spec: str, stock: int, goods_name: str = None):
    """更新库存"""
    ensure_dirs()
    inventory = load_inventory()

    found = False
    for item in inventory:
        if item["sku_spec"] == sku_spec:
            if goods_name:
                item["goods_name"] = goods_name
            item["total_stock"] = stock
            item["low_stock_warning"] = stock < item.get("reorder_point", REORDER_POINT)
            item["last_updated"] = datetime.now().isoformat()
            found = True
            log(f"库存更新: {sku_spec} → {stock}", "OK")
            break

    if not found:
        item = {
            "goods_name": goods_name or "手动录入",
            "sku_spec": sku_spec,
            "total_stock": stock,
            "sold_today": 0,
            "sold_7d": 0,
            "low_stock_warning": stock < REORDER_POINT,
            "reorder_point": REORDER_POINT,
            "last_updated": datetime.now().isoformat(),
        }
        inventory.append(item)
        log(f"新增库存: {sku_spec} → {stock}", "OK")

    save_inventory(inventory)


def cmd_check():
    """库存预警检查"""
    inventory = load_inventory()
    if not inventory:
        log("库存数据为空，请先 --init", "WARN")
        return

    warnings = [i for i in inventory if i.get("low_stock_warning")]
    out_of_stock = [i for i in inventory if i.get("total_stock", 0) <= 0]

    print(f"\n  {'='*55}")
    print(f"  库存预警报告")
    print(f"  总SKU: {len(inventory)}  预警: {len(warnings)}  缺货: {len(out_of_stock)}")
    print(f"  {'='*55}")

    if out_of_stock:
        print(f"\n  ❌ 缺货 SKU:")
        for item in out_of_stock:
            print(f"    {item['goods_name'][:20]:20s} | {item['sku_spec']:12s} | 库存: {item['total_stock']}")

    if warnings:
        print(f"\n  ⚠️ 低库存 SKU:")
        for item in sorted(warnings, key=lambda x: x["total_stock"]):
            sold_7d = item.get("sold_7d", 0)
            stock = item["total_stock"]
            days_left = stock / max(sold_7d / 7, 1) if sold_7d > 0 else 999
            print(f"    {item['goods_name'][:20]:20s} | {item['sku_spec']:12s} "
                  f"| 库存: {stock:3d} | 7日销量: {sold_7d:2d} | 可售: {days_left:.0f}天")

    if not out_of_stock and not warnings:
        print("\n  ✅ 库存正常")

    print(f"  {'='*55}")


def cmd_reorder():
    """生成补货建议"""
    inventory = load_inventory()
    if not inventory:
        log("库存数据为空，请先 --init", "WARN")
        return

    needs_reorder = [i for i in inventory
                     if i.get("total_stock", 0) < i.get("reorder_point", REORDER_POINT)
                     or i.get("sold_7d", 0) > i.get("total_stock", 0) * 0.5]

    print(f"\n  {'='*55}")
    print(f"  补货建议")
    print(f"  {'='*55}")

    if not needs_reorder:
        print("\n  ✅ 暂无补货需求")
        print(f"  {'='*55}")
        return

    for item in sorted(needs_reorder, key=lambda x: x["total_stock"]):
        sold_7d = item.get("sold_7d", 0)
        stock = item["total_stock"]
        reorder_qty = max(sold_7d - stock, 10)  # 至少补10件
        print(f"\n  📦 {item['goods_name']}")
        print(f"    规格: {item['sku_spec']}")
        print(f"    当前: {stock}  7日销: {sold_7d}")
        print(f"    ➡️  建议补货: {reorder_qty} 件")

    print(f"\n  {'='*55}")


def main():
    parser = argparse.ArgumentParser(
        description="库存预警 — 初始化/更新/预警/补货建议",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--init", action="store_true", help="初始化库存（从 listing-ready/ 导入）")
    parser.add_argument("--update", type=str, help="更新SKU库存 (sku_spec)")
    parser.add_argument("--stock", type=int, default=200, help="库存数量")
    parser.add_argument("--goods", type=str, help="商品名称")
    parser.add_argument("--check", action="store_true", help="库存预警检查")
    parser.add_argument("--reorder", action="store_true", help="生成补货建议")

    args = parser.parse_args()

    if args.init:
        cmd_init()
    elif args.update:
        cmd_update(args.update, args.stock, args.goods)
    elif args.check:
        cmd_check()
    elif args.reorder:
        cmd_reorder()
    else:
        cmd_check()


if __name__ == "__main__":
    main()
