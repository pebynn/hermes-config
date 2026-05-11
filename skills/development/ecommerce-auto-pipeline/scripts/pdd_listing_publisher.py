#!/usr/bin/env python3
"""
listing-ready → PDD 发布适配层 v1.0

读取 listing-ready/ 数据 → 记录发布状态 → 调用 pdd_listing.py 执行发布

用法:
    # 预览所有就绪商品
    python pdd_listing_publisher.py --date 2026-04-28 --preview

    # 发布所有就绪商品（调用 pdd_listing.py）
    python pdd_listing_publisher.py --date 2026-04-28 --publish

    # 发布单个商品
    python pdd_listing_publisher.py --input /path/to/product --publish
"""

import os
import sys
import json
import time
import subprocess
import argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_ROOT = os.path.expanduser("~/PDD/商品")
PDD_LISTING_SCRIPT = os.path.join(SCRIPT_DIR, "pdd_listing.py")


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "STEP": "📌"}.get(level, "•")
    print(f"  {icon} [{ts}] {msg}")


def find_listing_ready_dirs(date_str: str = None, input_path: str = None) -> list:
    """查找所有含 listing-ready/listing.json 的商品目录"""
    if input_path:
        if os.path.isfile(input_path):
            input_path = os.path.dirname(input_path)
        listing_file = os.path.join(input_path, "listing-ready", "listing.json")
        if os.path.isfile(listing_file):
            return [input_path]
        log(f"未找到 listing.json: {input_path}", "WARN")
        return []

    base = os.path.join(OUTPUT_ROOT, date_str or time.strftime("%Y-%m-%d"))
    if not os.path.isdir(base):
        log(f"日期目录不存在: {base}", "ERR")
        return []

    dirs = []
    seen = set()
    for root, dirs_here, files in os.walk(base):
        if "listing-ready" in dirs_here:
            lf = os.path.join(root, "listing-ready", "listing.json")
            if os.path.isfile(lf):
                dir_name = os.path.basename(root)
                if dir_name not in seen:
                    seen.add(dir_name)
                    dirs.append(root)
                dirs_here.remove("listing-ready")

    dirs.sort(key=lambda d: os.path.basename(d))
    return dirs


def write_publish_result(product_dir: str, result: dict):
    """写入发布结果到商品目录"""
    output_path = os.path.join(product_dir, "publish_result.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log(f"发布结果已保存: {output_path}", "OK")


def preview_mode(product_dirs: list) -> list:
    """预览模式：输出所有就绪商品的摘要"""
    results = []
    for d in product_dirs:
        lf = os.path.join(d, "listing-ready", "listing.json")
        with open(lf, "r", encoding="utf-8") as f:
            listing = json.load(f)

        dir_name = os.path.basename(d)
        price_yuan = listing.get("goods_price", 0) / 100
        sku_count = len(listing.get("sku_list", []))
        img_count_main = len(listing.get("main_images", []))
        img_count_detail = len(listing.get("detail_images", []))
        tier = listing.get("pricing", {}).get("tier", "profit")

        print(f"\n  📦 {dir_name}")
        print(f"    标题: {listing.get('goods_name', '?')[:50]}")
        print(f"    售价: ¥{price_yuan:.1f}  ({tier})")
        print(f"    SKU: {sku_count}  主图: {img_count_main}  详情: {img_count_detail}")

        result = {
            "goods_name": listing.get("goods_name", ""),
            "input_dir": d,
            "publish_time": datetime.now().isoformat(),
            "status": "previewed",
            "pricing_tier": tier,
            "final_price": price_yuan,
            "images_uploaded": img_count_main + img_count_detail,
            "sku_count": sku_count,
        }
        write_publish_result(d, result)
        results.append(result)

    return results


def publish_mode(product_dirs: list, headless: bool = False) -> list:
    """发布模式：调用 pdd_listing.py 逐个发布"""
    results = []
    for i, d in enumerate(product_dirs):
        dir_name = os.path.basename(d)
        print(f"\n{'─'*50}")
        log(f"[{i+1}/{len(product_dirs)}] 发布: {dir_name}", "STEP")

        # 读取 listing.json 获取发布前信息
        lf = os.path.join(d, "listing-ready", "listing.json")
        try:
            with open(lf, "r", encoding="utf-8") as f:
                listing = json.load(f)
        except Exception as e:
            log(f"读取 listing.json 失败: {e}", "ERR")
            results.append({
                "goods_name": dir_name,
                "input_dir": d,
                "publish_time": datetime.now().isoformat(),
                "status": "failed",
                "error": f"读取 listing.json 失败: {e}",
            })
            continue

        # 调用 pdd_listing.py
        cmd = [sys.executable, PDD_LISTING_SCRIPT, "--input", d, "--publish"]
        if headless:
            cmd.append("--headless")

        try:
            result = subprocess.run(cmd, timeout=600)
            success = result.returncode == 0
            status = "published" if success else "failed"
            log(f"{'发布成功' if success else '发布失败'} ({result.returncode})", "OK" if success else "ERR")
        except subprocess.TimeoutExpired:
            log("发布超时（>600s）", "ERR")
            status = "failed"
        except Exception as e:
            log(f"发布异常: {e}", "ERR")
            status = "failed"

        price_yuan = listing.get("goods_price", 0) / 100
        pub_result = {
            "goods_name": listing.get("goods_name", dir_name),
            "input_dir": d,
            "publish_time": datetime.now().isoformat(),
            "status": status,
            "pdd_goods_id": None,
            "preview_url": None,
            "error": None if status == "published" else f"exit code != 0",
            "pricing_tier": listing.get("pricing", {}).get("tier", "profit"),
            "final_price": price_yuan,
            "images_uploaded": len(listing.get("main_images", [])) + len(listing.get("detail_images", [])),
            "sku_count": len(listing.get("sku_list", [])),
        }
        write_publish_result(d, pub_result)
        results.append(pub_result)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="listing-ready → PDD 发布适配层",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--input", "-i", type=str, help="商品目录路径")
    group.add_argument("--date", "-d", type=str, help="日期 YYYY-MM-DD，默认今天")

    parser.add_argument("--preview", action="store_true", help="预览模式")
    parser.add_argument("--publish", action="store_true", help="发布模式")
    parser.add_argument("--headless", action="store_true", help="headless 模式")

    args = parser.parse_args()
    today = time.strftime("%Y-%m-%d")
    date_str = args.date or today

    if not args.preview and not args.publish:
        args.preview = True
        log("未指定模式，默认预览", "INFO")

    # 查找商品
    product_dirs = find_listing_ready_dirs(date_str, args.input)
    if not product_dirs:
        log(f"未找到就绪商品 (date={date_str})", "ERR")
        sys.exit(1)

    log(f"找到 {len(product_dirs)} 个就绪商品", "OK")
    for d in product_dirs:
        log(f"  {os.path.basename(d)}", "INFO")

    # 执行
    if args.preview:
        results = preview_mode(product_dirs)
    else:
        results = publish_mode(product_dirs, args.headless)

    # 汇总
    print(f"\n{'='*50}")
    success_count = sum(1 for r in results if r["status"] in ("published", "previewed"))
    fail_count = sum(1 for r in results if r["status"] == "failed")
    log(f"汇总: {success_count} 成功, {fail_count} 失败 / 共 {len(results)}", "OK" if fail_count == 0 else "WARN")
    print(f"{'='*50}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
