#!/usr/bin/env python3
"""pre_kanban_create.py — B层代码强制注入 (对标 enforce_delegate.py)
在 kanban_create 前自动执行：教训注入 + 成本预估 + 指令优化
用法：python3 pre_kanban_create.py --domain <domain> --body <task_body>
输出：注入后的task body（stdout），注入标记写stderr
退出码0=成功，1=成本熔断，2=其他错误
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
LESSONS_DIR = HERMES_HOME / "lessons"
GLOBAL_LESSONS = LESSONS_DIR / "global.md"

# 域→lessons文件映射
DOMAIN_LESSONS_MAP = {
    "code-domain": "code-domain.md",
    "code": "code-domain.md",
    "ops-domain": "ops-domain.md",
    "ops": "ops-domain.md",
    "finance-domain": "finance-domain.md",
    "finance": "finance-domain.md",
    "research-domain": "research-domain.md",
    "research": "research-domain.md",
    "writer": "writing-domain.md",
    "reviewer": "writing-domain.md",
    "ec-sourcing": "ec-domain.md",
    "ec-listing": "ec-domain.md",
    "ec-fulfillment": "ec-domain.md",
    "ec": "ec-domain.md",
}

def extract_critical_lessons(filepath: Path) -> list[str]:
    """从lessons文件提取🔴CRITICAL条目"""
    if not filepath.exists():
        return []
    
    content = filepath.read_text(encoding='utf-8')
    lessons = []
    in_critical = False
    
    for line in content.split('\n'):
        if '## 🔴 CRITICAL' in line or '## 🔴' in line:
            in_critical = True
            continue
        elif in_critical and (line.startswith('## ') or line.startswith('# ')):
            break
        elif in_critical and line.startswith('### '):
            # 子条目标题
            lessons.append(line.replace('### ', '').strip())
            continue
        elif in_critical and line.strip().startswith('- **'):
            lessons.append(line.strip())
    
    return lessons

def format_lesson_block(lessons: list[str], domain: str) -> str:
    """格式化教训块"""
    if not lessons:
        return ""
    
    lines = [
        "╔══════════════════════════════════════════════╗",
        "║  ⚠️ 已知陷阱 — 本次任务执行前必读            ║",
        f"║  域: {domain:<38}║",
        "╚══════════════════════════════════════════════╝",
        ""
    ]
    for lesson in lessons[:8]:  # 最多8条避免token浪费
        lines.append(f"  {lesson}")
    lines.append("")
    return '\n'.join(lines)

def check_cost(domain: str) -> dict:
    """检查今日成本（简化版，不依赖MCP）"""
    cost_file = HERMES_HOME / "data" / "cost_tracker.json"
    try:
        if cost_file.exists():
            data = json.loads(cost_file.read_text())
            today = data.get("today", {})
            cost = today.get("estimated_cost_usd", 0)
            return {"cost": cost, "warning": cost > 5, "blocked": cost > 8}
    except Exception:
        pass
    return {"cost": 0, "warning": False, "blocked": False}

def main():
    parser = argparse.ArgumentParser(description="B层强制注入 — kanban_create前置")
    parser.add_argument("--domain", required=True, help="Worker域名 (如 finance-domain)")
    parser.add_argument("--body", help="任务body（可从stdin读）")
    parser.add_argument("--body-file", help="任务body文件路径")
    parser.add_argument("--json", action="store_true", help="JSON输出模式")
    parser.add_argument("--dry-run", action="store_true", help="只检查不注入")
    args = parser.parse_args()

    # 获取body
    body = args.body
    if not body and args.body_file:
        body = Path(args.body_file).read_text(encoding='utf-8')
    if not body:
        body = sys.stdin.read().strip()

    # 解析域→文件名
    lesson_file_name = DOMAIN_LESSONS_MAP.get(args.domain)
    if not lesson_file_name:
        # 模糊匹配
        for key, val in DOMAIN_LESSONS_MAP.items():
            if key in args.domain or args.domain in key:
                lesson_file_name = val
                break
        if not lesson_file_name:
            lesson_file_name = "global.md"  # fallback

    # 加载教训
    domain_lessons = extract_critical_lessons(LESSONS_DIR / lesson_file_name)
    global_lessons = extract_critical_lessons(GLOBAL_LESSONS)

    # 去重合并
    seen = set()
    all_lessons = []
    for l in global_lessons + domain_lessons:
        key = l[:50]
        if key not in seen:
            all_lessons.append(l)
            seen.add(key)

    # 成本检查
    cost_info = check_cost(args.domain)

    # 输出
    if args.json:
        result = {
            "domain": args.domain,
            "lesson_file": lesson_file_name,
            "lessons_injected": len(all_lessons),
            "cost_usd": cost_info["cost"],
            "cost_warning": cost_info["warning"],
            "cost_blocked": cost_info["blocked"],
            "enriched_body": "",
            "status": "ok"
        }
        if cost_info["blocked"]:
            result["status"] = "blocked"
            result["error"] = f"今日成本${cost_info['cost']:.2f}超过$8熔断线"
        elif not body:
            result["status"] = "no_body"
        else:
            lesson_block = format_lesson_block(all_lessons, args.domain)
            result["enriched_body"] = f"{lesson_block}\n---\n{body}" if lesson_block else body
        
        print(json.dumps(result, ensure_ascii=False))
    else:
        if cost_info["blocked"]:
            print(f"❌ COST BLOCKED: 今日成本${cost_info['cost']:.2f}超过$8熔断线", file=sys.stderr)
            sys.exit(1)
        
        if cost_info["warning"]:
            print(f"⚠️  COST WARNING: 今日成本${cost_info['cost']:.2f}超过$5预警线", file=sys.stderr)
        
        lesson_block = format_lesson_block(all_lessons, args.domain)
        if lesson_block and body:
            print(f"{lesson_block}\n---\n{body}")
        elif body:
            print(body)
        
        print(f"[B层注入] domain={args.domain} lessons={len(all_lessons)} cost=${cost_info['cost']:.2f}", file=sys.stderr)

    # 退出码
    if cost_info["blocked"]:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
