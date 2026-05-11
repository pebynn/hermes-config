#!/usr/bin/env python3
"""
电商一站式管线 模拟运行脚本
模拟生成产品数据 → 跑完 sourcing→listing→ops 全流程，无需外部依赖。
"""

import os
import sys
import json
import time
import shutil
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FULFILLMENT_DIR = os.path.join(SCRIPT_DIR, "fulfillment")
PREPARE_SCRIPT = os.path.join(SCRIPT_DIR, "prepare_listing.py")
PUBLISHER_SCRIPT = os.path.join(SCRIPT_DIR, "pdd_listing_publisher.py")
OUTPUT_ROOT = os.path.expanduser("~/PDD/商品")
OPS_ROOT = os.path.expanduser("~/PDD/运营")
SIM_DATE = "2026-04-28"  # 模拟日期用当天

MOCK_PRODUCTS = [
    {
        "shop_name": "旗舰工厂",
        "goods_no": "M001",
        "shop_address": "https://cs.17zwd.com/shop/mock01",
        "title": "妈妈夏装冰丝短袖宽松显瘦上衣 中老年女装大码雪纺衫",
        "price": 35,
        "sku": {"colors": ["黑色", "藏青", "碎花", "酒红"], "sizes": ["L", "XL", "2XL", "3XL"]},
        "main_count": 4,
        "detail_count": 8,
    },
    {
        "shop_name": "精品服饰",
        "goods_no": "M002",
        "shop_address": "https://cs.17zwd.com/shop/mock02",
        "title": "中老年妈妈装两件套 夏季冰丝套装女 宽松显瘦休闲家居服",
        "price": 55,
        "sku": {"colors": ["深蓝", "粉色", "浅灰"], "sizes": ["XL", "2XL", "3XL", "4XL", "5XL"]},
        "main_count": 5,
        "detail_count": 6,
    },
    {
        "shop_name": "时尚女装批发",
        "goods_no": "M003",
        "shop_address": "https://cs.17zwd.com/shop/mock03",
        "title": "阔腿裤女夏高腰垂感显瘦直筒裤 宽松冰丝妈妈装中老年",
        "price": 29,
        "sku": {"colors": ["黑色", "藏青", "卡其"], "sizes": ["L", "XL", "2XL", "3XL"]},
        "main_count": 3,
        "detail_count": 5,
    },
    {
        "shop_name": "雅致女装",
        "goods_no": "M004",
        "shop_address": "https://cs.17zwd.com/shop/mock04",
        "title": "中老年真丝衬衫女2026新款 妈妈装短袖气质印花上衣",
        "price": 68,
        "sku": {"colors": ["碎花", "杏色", "浅蓝"], "sizes": ["L", "XL", "2XL"]},
        "main_count": 4,
        "detail_count": 7,
    },
    {
        "shop_name": "舒适居家",
        "goods_no": "M005",
        "shop_address": "https://cs.17zwd.com/shop/mock05",
        "title": "广场舞服装套装夏季中老年女装 运动休闲两件套宽松显瘦",
        "price": 45,
        "sku": {"colors": ["红色", "蓝色", "玫红"], "sizes": ["均码"]},
        "main_count": 5,
        "detail_count": 4,
    },
]


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "STEP": "📌", "TITLE": "🚀"}.get(level, "•")
    print(f"  {icon} [{ts}] {msg}")


def create_mock_products(base_dir):
    """生成模拟商品目录（模拟 pipeline.py + download_from_17zwd.py 的输出）"""
    if os.path.isdir(base_dir):
        shutil.rmtree(base_dir)
    os.makedirs(base_dir, exist_ok=True)

    from PIL import Image
    img_available = False
    try:
        img = Image.new("RGB", (800, 800), color="white")
        img_available = True
    except ImportError:
        log("Pillow 不可用，跳过图片生成", "WARN")

    count = 0
    for prod in MOCK_PRODUCTS:
        dir_name = f"{prod['shop_name']}-{prod['goods_no']}"
        prod_dir = os.path.join(base_dir, dir_name)
        os.makedirs(prod_dir, exist_ok=True)

        # 写 _店铺信息.json
        shop_info = {
            "shop_name": prod["shop_name"],
            "goods_no": prod["goods_no"],
            "shop_address": prod["shop_address"],
            "title": prod["title"],
            "price": prod["price"],
            "sku": prod["sku"],
        }
        with open(os.path.join(prod_dir, "_店铺信息.json"), "w", encoding="utf-8") as f:
            json.dump(shop_info, f, ensure_ascii=False, indent=2)

        # 生成模拟图片目录
        for sub_dir, count_key in [("主图", "main_count"), ("详情图", "detail_count")]:
            img_dir = os.path.join(prod_dir, sub_dir)
            os.makedirs(img_dir, exist_ok=True)
            if img_available:
                for i in range(prod[count_key]):
                    img_path = os.path.join(img_dir, f"{sub_dir}_{i+1}.jpg")
                    img.save(img_path, "JPEG", quality=85)

        count += 1
        log(f"创建: {dir_name}  ({prod['price']}元, {len(prod['sku']['colors'])}色×{len(prod['sku']['sizes'])}码)", "OK")

    return count


def main():
    base_dir = os.path.join(OUTPUT_ROOT, SIM_DATE)
    print(f"\n{'='*55}")
    log("电商一站式管线 — 模拟运行", "TITLE")
    log(f"日期: {SIM_DATE}", "INFO")
    print(f"{'='*55}")

    # ── 阶段1: 模拟 sourcing 输出 ──
    print(f"\n{'─'*55}")
    log("Phase 1: 模拟选品产出（跳过 17网 下载）", "TITLE")
    print(f"{'─'*55}")
    count = create_mock_products(base_dir)
    log(f"创建 {count} 个模拟商品", "OK")

    # ── 阶段2: prepare_listing 上架准备（正式生成数据）──
    print(f"\n{'─'*55}")
    log("Phase 2: 上架准备（图片处理 + AI标题 + 定价 + SKU）", "TITLE")
    print(f"{'─'*55}")
    rc = os.system(f"python3 {PREPARE_SCRIPT} --date {SIM_DATE} --tier profit")
    if rc != 0:
        log("prepare_listing 失败", "ERR")
    else:
        log("上架数据已写入 listing-ready/", "OK")

    # 快速预览结果
    print(f"\n{'─'*55}")
    log("Phase 2b: 上架预览摘要", "TITLE")
    print(f"{'─'*55}")
    os.system(f"python3 {PREPARE_SCRIPT} --date {SIM_DATE} --preview --tier profit")

    # ── 阶段3: pdd_listing_publisher 发布预览 ──
    print(f"\n{'─'*55}")
    log("Phase 3: 上架发布预览（跳过浏览器扫码）", "TITLE")
    print(f"{'─'*55}")
    os.system(f"python3 {PUBLISHER_SCRIPT} --date {SIM_DATE} --preview")

    # ── 阶段4: 运营数据生成 ──
    print(f"\n{'─'*55}")
    log("Phase 4: 运营数据模拟", "TITLE")
    print(f"{'─'*55}")
    os.system(f"python3 {os.path.join(FULFILLMENT_DIR, '1_order_import.py')} --date {SIM_DATE} --generate --count 8")
    os.system(f"python3 {os.path.join(FULFILLMENT_DIR, '2_return_refund.py')} --date {SIM_DATE} --generate --count 3")
    os.system(f"python3 {os.path.join(FULFILLMENT_DIR, '3_review_manager.py')} --date {SIM_DATE} --generate --count 6")
    os.system(f"python3 {os.path.join(FULFILLMENT_DIR, '4_inventory_warning.py')} --init")
    os.system(f"python3 {os.path.join(FULFILLMENT_DIR, '4_inventory_warning.py')} --check")

    # ── 阶段5: 运营看板 ──
    print(f"\n{'─'*55}")
    log("Phase 5: 运营看板", "TITLE")
    print(f"{'─'*55}")
    os.system(f"python3 {os.path.join(FULFILLMENT_DIR, '5_dashboard.py')} --date {SIM_DATE}")

    # ── 汇总报告 ──
    print(f"\n{'='*55}")
    log("模拟运行完成!", "TITLE")
    print(f"  选品: {count} 个商品 → {base_dir}/")
    print(f"  运营: {OPS_ROOT}/")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
