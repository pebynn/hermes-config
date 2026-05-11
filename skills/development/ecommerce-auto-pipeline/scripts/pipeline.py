#!/usr/bin/env python3
"""
电商全自动管线 v1.0 — 关键词采集 → 搜索17网 → 下载解压

流程：
  1. collect_hot_words.py 采集三大平台关键词
  2. 保存关键词到临时文件
  3. 调用 download_from_17zwd.py --keywords-file 搜索+下载+解压

用法：
    python pipeline.py --username 账号 --password 密码
    python pipeline.py --keywords "短袖,裤子" --username 账号 --password 密码
    python pipeline.py --cross-only --recursive --max 10 --username 账号 --password 密码
"""

import sys
import os
import json
import time
import subprocess
import argparse
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COLLECT_SCRIPT = os.path.join(SCRIPT_DIR, "collect_hot_words.py")
DOWNLOAD_SCRIPT = os.path.join(SCRIPT_DIR, "download_from_17zwd.py")
OUTPUT_ROOT = os.path.expanduser("~/PDD/商品")

DEFAULT_SEEDS = [
    "中老年女装", "妈妈装", "奶奶装",
    "妈妈装套装", "中老年套装", "运动套装女", "休闲套装",
    "唐装女", "改良旗袍", "新中式女装",
    "阔腿裤", "雪纺衫",
    "显瘦妈妈装", "宽松大码", "纯棉女装",
    "冰丝夏装",
    "广场舞服装", "婚庆妈妈装", "休闲居家套装",
]


def main():
    parser = argparse.ArgumentParser(
        description="电商选品全自动管线 — 采集→搜索→下载→解压",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python pipeline.py --username 13800138000 --password xxx
  python pipeline.py --keywords "妈妈装" --max 5 --username 13800138000 --password xxx
  python pipeline.py --no-collect --keywords-file ./my_words.txt --username 13800138000 --password xxx
        """,
    )
    parser.add_argument("--keywords", "-k", type=str,
                        help="直接指定关键词（逗号分隔）")
    parser.add_argument("--keywords-file", type=str,
                        help="关键词文件（每行一个词），跳过采集")
    parser.add_argument("--no-collect", action="store_true",
                        help="跳过采集阶段")
    parser.add_argument("--cross-only", "-c", action="store_true",
                        help="仅用跨平台验证的词")
    parser.add_argument("--no-recursive", action="store_true",
                        help="禁用递归展开")
    parser.add_argument("--max-keywords", type=int, default=8,
                        help="最多用几个关键词（默认8）")
    parser.add_argument("--max-per-keyword", type=int, default=2,
                        help="每关键词最多下载几个（默认2）")
    parser.add_argument("--max", type=int, default=10,
                        help="总下载数上限（默认10）")
    parser.add_argument("--debug", action="store_true",
                        help="调试模式")
    parser.add_argument("--username", type=str, default="",
                        help="17网账号")
    parser.add_argument("--password", type=str, default="",
                        help="17网密码（建议通过 HERMES_ZW_PASSWORD 环境变量传入）")

    parser.add_argument("--output", "-o", type=str, default="",
                        help="输出目录")

    args = parser.parse_args()

    # 环境变量优先于命令行参数
    env_password = os.environ.get("HERMES_ZW_PASSWORD")
    if env_password:
        if args.password:
            print("  ⚠️ --password 参数将被 HERMES_ZW_PASSWORD 环境变量覆盖")
        args.password = env_password

    today = time.strftime("%Y-%m-%d")
    output_dir = args.output or os.path.join(OUTPUT_ROOT, today)

    print(f"{'='*55}")
    print(f"🚀 电商选品管线 v1.0")
    print(f"{'='*55}")
    print(f"  日期: {today}")
    print(f"  输出: {output_dir}")
    print(f"{'='*55}")

    keywords_temp = None

    # ── 阶段1：获取关键词 ──
    print(f"\n{'─'*55}")
    print("  阶段1/2: 关键词")
    print(f"{'─'*55}")

    if args.keywords_file:
        # 直接用已有文件
        print(f"  使用关键词文件: {args.keywords_file}")
        keywords_temp = args.keywords_file
        with open(keywords_temp) as f:
            kw_count = sum(1 for l in f if l.strip())
        print(f"  ✅ {kw_count} 个词")

    elif args.keywords:
        # 命令行指定
        words = [s.strip() for s in args.keywords.split(",") if s.strip()]
        keywords_temp = f"/tmp/pipeline_keywords_{int(time.time())}.txt"
        with open(keywords_temp, "w", encoding="utf-8") as f:
            for w in words:
                f.write(w + "\n")
        print(f"  自定义关键词: {', '.join(words)}")
        print(f"  ✅ {len(words)} 个词")

    elif args.no_collect:
        print("  ⏭ 跳过采集，使用默认种子词")
        words = DEFAULT_SEEDS
        keywords_temp = f"/tmp/pipeline_keywords_{int(time.time())}.txt"
        with open(keywords_temp, "w", encoding="utf-8") as f:
            for w in words:
                f.write(w + "\n")
        print(f"  ✅ {len(words)} 个默认种子词")

    else:
        # 调用 collect_hot_words.py，输出 JSON 到文件
        print("  🔍 采集三大平台热词...")
        ts = int(time.time())
        json_out = f"/tmp/collect_result_{ts}.json"
        cmd = [sys.executable, COLLECT_SCRIPT,
               "--top", "50",
               "--output-json", json_out]
        if args.cross_only:
            cmd.append("--cross-only")
        if not args.no_recursive:
            cmd.append("--recursive")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"  ❌ 采集失败:\n{result.stderr}")
            return

        # 从 JSON 文件读取结果
        if not os.path.exists(json_out):
            print(f"  ❌ 采集未生成结果文件: {json_out}")
            return

        with open(json_out, "r", encoding="utf-8") as f:
            collect_data = json.load(f)

        hot_words = collect_data.get("hot_words", [])
        if not hot_words:
            print("  ❌ 无关键词输出，退出")
            return

        # 取前N个关键词
        selected = hot_words[:args.max_keywords]
        keywords_temp = f"/tmp/pipeline_keywords_{int(time.time())}.txt"
        with open(keywords_temp, "w", encoding="utf-8") as f:
            for item in selected:
                f.write(item["word"] + "\n")

        print(f"  ✅ 选定 {len(selected)} 个关键词:")
        for i, item in enumerate(selected):
            tag = " 🔀" if item.get("is_cross") else ""
            plat_str = ", ".join(item["platforms"])
            print(f"    #{i+1} {item['word']:<25s} [{plat_str}]{tag}")

    # ── 阶段2：搜索+下载 ──
    print(f"\n{'─'*55}")
    print("  阶段2/2: 搜索 + 下载")
    print(f"{'─'*55}")

    dl_cmd = [
        sys.executable, DOWNLOAD_SCRIPT,
        "--keywords-file", keywords_temp,
        "--max-keywords", str(args.max_keywords),
        "--max-per-keyword", str(args.max_per_keyword),
        "--max", str(args.max),
        "--output", output_dir,
        "--extract-to", output_dir,
    ]
    if args.username:
        dl_cmd.extend(["--username", args.username])
    if args.password:
        dl_cmd.extend(["--password", args.password])
    if args.debug:
        dl_cmd.append("--debug")

    print("  开始搜索并下载...")
    result = subprocess.run(dl_cmd)
    if result.returncode != 0:
        print(f"  ⚠️ 下载脚本返回非0退出码({result.returncode})，可能部分商品下载失败")

    # 清理临时文件
    if keywords_temp and keywords_temp != args.keywords_file:
        try:
            os.unlink(keywords_temp)
        except OSError:
            pass

    print(f"\n{'='*55}")
    print(f"✅ 管线完成")
    print(f"  输出目录: {output_dir}")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
