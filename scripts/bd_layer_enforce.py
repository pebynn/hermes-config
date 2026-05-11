#!/usr/bin/env python3
"""bd_layer_enforce.py — B+D层统一执行入口
用法：
  注入body: python3 bd_layer_enforce.py inject --domain finance-domain --body "任务描述"
  回收lessons: python3 bd_layer_enforce.py recover --domain finance-domain --result "worker返回文本"
  一键注入+创建: python3 bd_layer_enforce.py wrap --domain finance-domain --title "任务名" --body "任务描述" --assignee finance-domain
"""

import sys
import os
import subprocess
import json
import argparse
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

def inject(domain: str, body: str) -> dict:
    """执行B层注入"""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "pre_kanban_create.py"),
         "--domain", domain, "--body", body, "--json"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return {"status": "blocked", "error": result.stderr}
    return json.loads(result.stdout)

def recover(domain: str, result_text: str) -> dict:
    """执行D层回收"""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "post_kanban_complete.py"),
         "--domain", domain, "--result", result_text, "--json"],
        capture_output=True, text=True, timeout=10
    )
    return json.loads(result.stdout) if result.returncode == 0 else {"lessons_found": 0}

def main():
    parser = argparse.ArgumentParser(description="B+D层统一执行入口")
    sub = parser.add_subparsers(dest="action")

    # inject
    p_inject = sub.add_parser("inject", help="B层注入：body中追加教训块")
    p_inject.add_argument("--domain", required=True)
    p_inject.add_argument("--body", required=True)
    p_inject.add_argument("--json", action="store_true")

    # recover
    p_recover = sub.add_parser("recover", help="D层回收：从result提取[LESSONS]")
    p_recover.add_argument("--domain", required=True)
    p_recover.add_argument("--result", required=True)
    p_recover.add_argument("--json", action="store_true")

    # wrap (一键注入+输出enriched body)
    p_wrap = sub.add_parser("wrap", help="一键注入：输出enriched body供kanban_create使用")
    p_wrap.add_argument("--domain", required=True)
    p_wrap.add_argument("--body", required=True)
    p_wrap.add_argument("--title", default="")
    p_wrap.add_argument("--assignee", default="")

    args = parser.parse_args()

    if args.action == "inject":
        result = inject(args.domain, args.body)
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            if result.get("status") == "blocked":
                print(f"BLOCKED: {result.get('error')}", file=sys.stderr)
                sys.exit(1)
            print(result.get("enriched_body", args.body))

    elif args.action == "recover":
        result = recover(args.domain, args.result)
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"回收{result.get('lessons_found', 0)}条教训")

    elif args.action == "wrap":
        result = inject(args.domain, args.body)
        if result.get("status") == "blocked":
            print(json.dumps({"error": "COST_BLOCKED", "detail": result.get("error")}))
            sys.exit(1)
        
        output = {
            "enriched_body": result.get("enriched_body", args.body),
            "lessons_injected": result.get("lessons_injected", 0),
            "cost_usd": result.get("cost_usd", 0),
            "cost_warning": result.get("cost_warning", False),
            "domain": args.domain,
            "title": args.title,
            "assignee": args.assignee,
            "status": "ready_for_kanban_create"
        }
        print(json.dumps(output, ensure_ascii=False))

if __name__ == "__main__":
    main()
