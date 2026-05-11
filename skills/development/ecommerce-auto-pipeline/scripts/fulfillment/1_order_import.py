#!/usr/bin/env python3
"""
1_order_import.py — 订单导入管理

支持：
- 模拟订单生成（无真实PDD API时用于测试）
- 订单列表/查看/状态管理
- 按日期/状态筛选

用法：
    # 生成模拟订单（当日）
    python 1_order_import.py --generate --count 5

    # 查看订单列表
    python 1_order_import.py --list

    # 查看订单详情
    python 1_order_import.py --view PDD202604280001

    # 更新订单状态
    python 1_order_import.py --update PDD202604280001 --status shipped

数据目录: ~/PDD/运营/orders/YYYY-MM-DD.json
"""

import os
import sys
import json
import time
import random
import argparse
from datetime import datetime, timedelta

OPS_ROOT = os.path.expanduser("~/PDD/运营")
ORDERS_DIR = os.path.join(OPS_ROOT, "orders")


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "STEP": "📌"}.get(level, "•")
    print(f"  {icon} [{ts}] {msg}")


def ensure_dirs():
    os.makedirs(ORDERS_DIR, exist_ok=True)


def get_orders_file(date_str: str = None) -> str:
    date_str = date_str or time.strftime("%Y-%m-%d")
    return os.path.join(ORDERS_DIR, f"{date_str}.json")


def load_orders(date_str: str = None) -> list:
    """加载指定日期的订单"""
    fpath = get_orders_file(date_str)
    if os.path.isfile(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_orders(orders: list, date_str: str = None):
    fpath = get_orders_file(date_str)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


def generate_mock_order(index: int) -> dict:
    """生成一条模拟订单（Contract C 格式）"""
    goods = [
        ("中老年妈妈夏装宽松显瘦连衣裙", "黑色,XL", 7990),
        ("中老年冰丝套装两件套", "深蓝,2XL", 8990),
        ("妈妈装雪纺衫短袖上衣", "碎花,L", 5990),
        ("中老年阔腿裤高腰", "藏青,3XL", 6990),
        ("广场舞服装套装", "红色,XL", 12990),
    ]
    goods_name, sku_spec, price = random.choice(goods)
    order_id = f"PDD{datetime.now().strftime('%Y%m%d')}{index:04d}"
    quantity = random.randint(1, 3)
    names = ["张**", "李**", "王**", "刘**", "陈**", "赵**"]
    phones = [f"138{random.randint(1000,9999)}{random.randint(0,9999):04d}" for _ in range(6)]

    return {
        "order_id": order_id,
        "create_time": datetime.now().isoformat(),
        "goods_name": goods_name,
        "sku_spec": sku_spec,
        "price": price,
        "quantity": quantity,
        "total": price * quantity,
        "buyer_name": random.choice(names),
        "buyer_phone": random.choice(phones),
        "shipping_address": f"广东省深圳市南山区{random.randint(100,999)}号",
        "status": "pending",
        "logistics": None,
        "remark": "",
    }


def cmd_generate(count: int, date_str: str):
    """生成模拟订单"""
    ensure_dirs()
    orders = load_orders(date_str)
    existing_ids = {o["order_id"] for o in orders}

    new_count = 0
    for i in range(count):
        order = generate_mock_order(len(orders) + i + 1)
        if order["order_id"] not in existing_ids:
            orders.append(order)
            existing_ids.add(order["order_id"])
            new_count += 1

    save_orders(orders, date_str)
    log(f"生成了 {new_count} 条新订单（共 {len(orders)} 条）", "OK")


def cmd_list(date_str: str, status: str = None):
    """列出订单"""
    orders = load_orders(date_str)
    if not orders:
        log(f"{date_str} 无订单数据", "INFO")
        return

    if status:
        orders = [o for o in orders if o.get("status") == status]

    print(f"\n  {'='*55}")
    print(f"  订单列表 ({date_str}) 共 {len(orders)} 条")
    if status:
        print(f"  筛选: status={status}")
    print(f"  {'='*55}")

    for o in orders:
        total_yuan = o["total"] / 100
        status_icon = {"pending": "⏳", "shipped": "📦", "returned": "↩️",
                       "refunded": "💰", "completed": "✅"}.get(o.get("status", ""), "•")
        print(f"  {status_icon} {o['order_id']}  {o['goods_name'][:20]:20s} "
              f"x{o['quantity']} ¥{total_yuan:.1f}  {o.get('status','')}")

    total_amount = sum(o["total"] for o in orders) / 100
    print(f"  {'─'*55}")
    print(f"  总金额: ¥{total_amount:.2f}")
    print(f"  {'='*55}")


def cmd_view(order_id: str, date_str: str = None):
    """查看订单详情"""
    if date_str:
        orders = load_orders(date_str)
        for o in orders:
            if o["order_id"] == order_id:
                print(f"\n  {'='*55}")
                print(f"  订单详情: {order_id}")
                print(f"  {'='*55}")
                for k, v in o.items():
                    if k in ("price", "total") and isinstance(v, (int, float)):
                        print(f"    {k}: ¥{v/100:.2f}")
                    else:
                        print(f"    {k}: {v}")
                print(f"  {'='*55}")
                return
        log(f"未找到订单: {order_id}", "WARN")
    else:
        # 在所有日期文件里找
        for fname in sorted(os.listdir(ORDERS_DIR), reverse=True):
            if fname.endswith(".json"):
                date_str = fname.replace(".json", "")
                orders = load_orders(date_str)
                for o in orders:
                    if o["order_id"] == order_id:
                        cmd_view(order_id, date_str)
                        return
        log(f"未找到订单: {order_id}", "WARN")


def cmd_update(order_id: str, new_status: str, date_str: str = None):
    """更新订单状态"""
    valid_statuses = ["pending", "shipped", "returned", "refunded", "completed"]
    if new_status not in valid_statuses:
        log(f"无效状态: {new_status}，可选: {', '.join(valid_statuses)}", "ERR")
        return

    found = False
    if date_str:
        orders = load_orders(date_str)
        for o in orders:
            if o["order_id"] == order_id:
                o["status"] = new_status
                found = True
                break
        if found:
            save_orders(orders, date_str)
            log(f"订单 {order_id} → {new_status}", "OK")
    else:
        for fname in sorted(os.listdir(ORDERS_DIR)):
            if fname.endswith(".json"):
                ds = fname.replace(".json", "")
                orders = load_orders(ds)
                for o in orders:
                    if o["order_id"] == order_id:
                        o["status"] = new_status
                        save_orders(orders, ds)
                        log(f"订单 {order_id} → {new_status} (in {ds})", "OK")
                        found = True
                        return

    if not found:
        log(f"未找到订单: {order_id}", "WARN")


def main():
    parser = argparse.ArgumentParser(
        description="订单导入管理 — 模拟订单生成/列表/详情/状态更新",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--date", "-d", type=str, help="日期 YYYY-MM-DD，默认今天")
    parser.add_argument("--generate", action="store_true", help="生成模拟订单")
    parser.add_argument("--count", type=int, default=5, help="生成数量")
    parser.add_argument("--list", action="store_true", help="列出订单")
    parser.add_argument("--view", type=str, help="查看订单详情 (order_id)")
    parser.add_argument("--update", type=str, help="更新订单 (order_id)")
    parser.add_argument("--status", type=str, help="订单状态: pending/shipped/returned/refunded/completed")
    parser.add_argument("--filter-status", type=str, help="筛选状态")

    args = parser.parse_args()
    today = time.strftime("%Y-%m-%d")
    date_str = args.date or today

    ensure_dirs()

    if args.generate:
        cmd_generate(args.count, date_str)
    elif args.list:
        cmd_list(date_str, args.filter_status)
    elif args.view:
        cmd_view(args.view, date_str)
    elif args.update:
        if not args.status:
            log("请指定 --status", "ERR")
            sys.exit(1)
        cmd_update(args.update, args.status, date_str)
    else:
        cmd_list(date_str)


if __name__ == "__main__":
    main()
