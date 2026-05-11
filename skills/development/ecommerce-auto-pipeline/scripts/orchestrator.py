#!/usr/bin/env python3
"""
电商一站式管线总控 v1.0 — 选品→上架→运营 全流程编排

用法:
    # 跑完整流程（选品→上架发布）
    python orchestrator.py --stage all --username 17825029430 --password 17825029430

    # 只跑选品阶段（采集→下载→上架准备）
    python orchestrator.py --stage sourcing --max 8

    # 只跑上架发布阶段
    python orchestrator.py --stage listing-only --preview
    python orchestrator.py --stage listing-only --publish

    # 只跑运营阶段（订单/售后/库存）
    python orchestrator.py --stage ops
"""

import os
import sys
import time
import subprocess
import argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_ROOT = os.path.expanduser("~/PDD/商品")
OPS_ROOT = os.path.expanduser("~/PDD/运营")

# 子脚本路径
PIPELINE_SCRIPT = os.path.join(SCRIPT_DIR, "pipeline.py")
PREPARE_SCRIPT = os.path.join(SCRIPT_DIR, "prepare_listing.py")
PUBLISHER_SCRIPT = os.path.join(SCRIPT_DIR, "pdd_listing_publisher.py")
PDD_LISTING_SCRIPT = os.path.join(os.path.expanduser("~/PDD"), "pdd_listing_v3.py")

# Fulfillment 模块
FULFILLMENT_DIR = os.path.join(SCRIPT_DIR, "fulfillment")
ORDER_SCRIPT = os.path.join(FULFILLMENT_DIR, "1_order_import.py")
RETURN_SCRIPT = os.path.join(FULFILLMENT_DIR, "2_return_refund.py")
REVIEW_SCRIPT = os.path.join(FULFILLMENT_DIR, "3_review_manager.py")
INVENTORY_SCRIPT = os.path.join(FULFILLMENT_DIR, "4_inventory_warning.py")
DASHBOARD_SCRIPT = os.path.join(FULFILLMENT_DIR, "5_dashboard.py")


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "STEP": "📌"}.get(level, "•")
    print(f"  {icon} [{ts}] {msg}")


def run_script(script_path: str, args: list, desc: str = "", timeout: int = 600) -> int:
    """运行子脚本，返回退出码"""
    print(f"\n{'='*55}")
    print(f"  📌 {desc or os.path.basename(script_path)}")
    print(f"{'='*55}")

    cmd = [sys.executable, script_path] + args
    log(f"执行: {' '.join(cmd)}", "INFO")

    try:
        result = subprocess.run(cmd, timeout=timeout)
        if result.returncode == 0:
            log(f"完成: {desc or os.path.basename(script_path)}", "OK")
        else:
            log(f"返回码 {result.returncode}: {desc}", "WARN")
        return result.returncode
    except subprocess.TimeoutExpired:
        log(f"超时 ({timeout}s): {desc}", "ERR")
        return -1
    except Exception as e:
        log(f"执行失败: {e}", "ERR")
        return -1


def stage_sourcing(args) -> int:
    """阶段1：选品 — 采集→搜索→下载→上架准备"""
    today = time.strftime("%Y-%m-%d")
    output_dir = os.path.join(OUTPUT_ROOT, today)

    # Step 1: pipeline.py (采集→搜索→下载)
    pipeline_args = [
        "--username", args.username,
        "--password", args.password,
        "--max", str(args.max),
        "--output", output_dir,
    ]
    if args.keywords:
        pipeline_args.extend(["--keywords", args.keywords])
    if args.no_collect:
        pipeline_args.append("--no-collect")
    if args.debug:
        pipeline_args.append("--debug")

    rc = run_script(PIPELINE_SCRIPT, pipeline_args, "Phase 1: 关键词采集 + 17网下载")
    if rc != 0 and not args.ignore_dl_errors:
        log("下载阶段有失败，是否继续由上架准备阶段决定", "WARN")

    # Step 2: prepare_listing.py (图片处理→AI标题→定价→SKU)
    prepare_args = ["--date", today, "--tier", args.tier]
    if args.preview:
        prepare_args.append("--preview")

    rc2 = run_script(PREPARE_SCRIPT, prepare_args, "Phase 2: 上架准备(图片/标题/定价/SKU)")

    # 输出汇总
    listing_dir = os.path.join(output_dir)
    if os.path.isdir(listing_dir):
        product_count = sum(1 for d in os.listdir(listing_dir)
                           if os.path.isdir(os.path.join(listing_dir, d)) and
                           os.path.isfile(os.path.join(listing_dir, d, "listing-ready", "listing.json")))
        log(f"上架准备完成: {product_count} 个商品就绪", "OK")
        log(f"输出目录: {listing_dir}/", "INFO")
    else:
        log(f"输出目录不存在: {listing_dir}", "WARN")

    return max(rc, rc2) if rc2 >= 0 else rc


def stage_listing(args) -> int:
    """阶段2：上架 — 消费 listing-ready 数据 → 发布到 PDD"""
    today = args.date or time.strftime("%Y-%m-%d")

    if args.publish:
        # 直接调用 pdd_listing.py 的 --date 发布
        pub_args = ["--date", today, "--publish"]
        if args.headless:
            pub_args.append("--headless")
        return run_script(PDD_LISTING_SCRIPT, pub_args, "Phase 3: 发布到拼多多商家后台")
    elif args.preview:
        # 预览模式
        preview_args = ["--date", today, "--preview"]
        return run_script(PDD_LISTING_SCRIPT, preview_args, "Phase 3: 预览上架数据")
    else:
        # 调用 publisher 做中间处理（写入 publish_result.json 等）
        pub_args = ["--date", today]
        return run_script(PUBLISHER_SCRIPT, pub_args, "Phase 3: listing-ready → 发布适配")


def stage_ops(args) -> int:
    """阶段3：运营 — 订单/售后/评价/库存/看板"""
    if not os.path.isdir(FULFILLMENT_DIR):
        log(f"运营模块目录不存在: {FULFILLMENT_DIR}", "WARN")
        log("请先运行 fulfillment 脚本初始化", "INFO")
        return -1

    ops_modules = {
        "order": (ORDER_SCRIPT, "订单管理"),
        "return": (RETURN_SCRIPT, "退货退款"),
        "review": (REVIEW_SCRIPT, "评价管理"),
        "inventory": (INVENTORY_SCRIPT, "库存预警"),
        "dashboard": (DASHBOARD_SCRIPT, "运营看板"),
    }

    if args.ops_module:
        selected = [args.ops_module]
    else:
        selected = list(ops_modules.keys())

    results = []
    for mod in selected:
        if mod not in ops_modules:
            log(f"未知模块: {mod}，可选: {', '.join(ops_modules.keys())}", "ERR")
            continue
        script_path, desc = ops_modules[mod]
        # inventory 不接受 --date 参数
        mod_args = []
        if mod != "inventory":
            mod_args = ["--date", args.date or time.strftime("%Y-%m-%d")]
        rc = run_script(script_path, mod_args, f"运营: {desc}")
        results.append((mod, rc))

    # 汇总
    print(f"\n{'='*55}")
    log("运营阶段汇总:", "INFO")
    for mod, rc in results:
        status = "✅" if rc == 0 else "❌"
        log(f"  {status} {mod}: exit={rc}", "INFO")
    print(f"{'='*55}")

    return max((rc for _, rc in results), default=0) if results else -1


def main():
    parser = argparse.ArgumentParser(
        description="电商一站式管线总控 — 选品→上架→运营 全流程编排",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用法示例:
  # 快速全流程（8件商品）
  python orchestrator.py --stage all --username 17825029430 --password 17825029430

  # 只选品预览
  python orchestrator.py --stage sourcing --preview

  # 只发布（用已有 listing-ready 数据）
  python orchestrator.py --stage listing-only --publish

  # 运营看板
  python orchestrator.py --stage ops --ops-module dashboard
        """,
    )

    # 阶段控制
    parser.add_argument("--stage", type=str, default="all",
                        choices=["all", "sourcing", "listing-only", "ops"],
                        help="执行阶段: all(全流程) / sourcing(选品) / listing-only(上架) / ops(运营)")
    parser.add_argument("--ops-module", type=str, default="",
                        help="运营阶段子模块: order/return/review/inventory/dashboard，默认全跑")

    # 选品参数
    parser.add_argument("--username", type=str, default="17825029430", help="17网账号")
    parser.add_argument("--password", type=str, default="17825029430", help="17网密码")
    parser.add_argument("--max", type=int, default=8, help="最大下载商品数（默认8）")
    parser.add_argument("--keywords", type=str, help="搜索关键词（逗号分隔），跳过采集")
    parser.add_argument("--no-collect", action="store_true", help="跳过采集阶段，用默认种子词")
    parser.add_argument("--tier", type=str, default="profit",
                        choices=["traffic", "profit", "image"],
                        help="定价策略: traffic(引流)/profit(利润)/image(形象)")

    # 上架参数
    parser.add_argument("--preview", action="store_true", help="预览模式（不发布）")
    parser.add_argument("--publish", action="store_true", help="发布模式")
    parser.add_argument("--headless", action="store_true", help="headless模式发布")
    parser.add_argument("--date", type=str, help="日期 YYYY-MM-DD，默认今天")

    # 其他
    parser.add_argument("--ignore-dl-errors", "--ide", action="store_true",
                        help="下载阶段有错误也继续")
    parser.add_argument("--debug", action="store_true", help="调试模式")

    args = parser.parse_args()
    today = time.strftime("%Y-%m-%d")
    if not args.date:
        args.date = today

    # ── Banner ──
    print(f"\n{'='*55}")
    print(f"  🚀 电商一站式管线 v1.0")
    print(f"  日期: {args.date}  阶段: {args.stage}")
    print(f"{'='*55}")

    results = []

    if args.stage in ("all", "sourcing"):
        rc = stage_sourcing(args)
        results.append(("sourcing", rc))

    if args.stage in ("all", "listing-only"):
        rc = stage_listing(args)
        results.append(("listing", rc))

    if args.stage == "ops":
        rc = stage_ops(args)
        results.append(("ops", rc))

    # ── 汇总报告 ──
    print(f"\n{'='*55}")
    print(f"  📊 管线执行报告")
    print(f"{'='*55}")
    all_ok = True
    for stage_name, rc in results:
        icon = "✅" if rc == 0 else ("⚠️" if rc > 0 else "❌")
        if rc != 0:
            all_ok = False
        print(f"  {icon} {stage_name}: exit={rc}")

    if all_ok:
        print(f"\n  🎉 全部完成!")
    else:
        print(f"\n  ⚠️ 部分阶段未通过，请检查上方日志")
    print(f"{'='*55}\n")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
