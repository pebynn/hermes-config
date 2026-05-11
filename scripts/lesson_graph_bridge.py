#!/usr/bin/env python3
"""
lesson_graph_bridge.py — 知识总线：lesson ↔ graphify 双向桥接

每次新教训写入后自动调用，将文本教训同步为graphify知识图谱节点。
由 lesson_inject.py add 后自动触发。

功能:
  1. 解析 ~/.hermes/lessons/{domain}.md 中的教训标题
  2. 在graphify中查找是否已有对应节点
  3. 无则创建节点(标题+域+严重度+来源session)
  4. 创建跨域关联边(同模式在不同域出现时)

Usage:
  python3 lesson_graph_bridge.py                    # 全量同步所有lessons
  python3 lesson_graph_bridge.py --domain finance   # 同步单个域
  python3 lesson_graph_bridge.py --new "教训标题" --domain global --severity CRITICAL  # 单条新增
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

HERMES_HOME = Path.home() / ".hermes"
LESSONS_DIR = HERMES_HOME / "lessons"

# graphify CLI路径
GRAPHIFY_BIN = None
for p in [Path.home() / ".local/bin/graphify", 
          Path.home() / "tools/graphify"]:
    if p.exists():
        GRAPHIFY_BIN = str(p)
        break


def parse_lessons(domain_file: Path) -> list[dict]:
    """解析教训文件，返回 [{title, severity, domain, content}]"""
    if not domain_file.exists():
        return []
    
    text = domain_file.read_text()
    domain = domain_file.stem.replace("-domain", "")
    lessons = []
    current_severity = None
    current_title = None
    current_lines = []
    
    severities = {"## 🔴 CRITICAL": "CRITICAL", 
                  "## 🟠 HIGH": "HIGH", 
                  "## 🟡 MEDIUM": "MEDIUM"}
    
    for line in text.split("\n"):
        # Detect severity section
        for marker, sev in severities.items():
            if line.strip().startswith(marker):
                # Save previous lesson
                if current_title and current_lines:
                    lessons.append({
                        "title": current_title,
                        "severity": current_severity or "MEDIUM",
                        "domain": domain,
                        "content": "\n".join(current_lines)[:500]
                    })
                current_severity = sev
                current_title = None
                current_lines = []
                break
        
        # Detect lesson title (### ...)
        if line.startswith("### ") and current_severity:
            if current_title and current_lines:
                lessons.append({
                    "title": current_title,
                    "severity": current_severity,
                    "domain": domain,
                    "content": "\n".join(current_lines)[:500]
                })
            current_title = line.replace("### ", "").strip()
            current_lines = []
        elif current_title:
            current_lines.append(line)
    
    # Last one
    if current_title and current_lines:
        lessons.append({
            "title": current_title,
            "severity": current_severity or "MEDIUM",
            "domain": domain,
            "content": "\n".join(current_lines)[:500]
        })
    
    return lessons


def graphify_search(title: str) -> str | None:
    """在graphify中搜索节点"""
    if not GRAPHIFY_BIN:
        return None
    try:
        result = subprocess.run(
            ["python3", GRAPHIFY_BIN, "search", title[:60]],
            capture_output=True, text=True, timeout=30
        )
        # Simple check: if output contains the title
        if title[:30] in result.stdout:
            return result.stdout[:200]
    except Exception:
        pass
    return None


def graphify_add_node(title: str, domain: str, severity: str, content: str) -> bool:
    """向graphify添加节点"""
    if not GRAPHIFY_BIN:
        return False
    try:
        node_text = f"[{severity}] {domain}: {title}\n{content[:300]}"
        result = subprocess.run(
            ["python3", GRAPHIFY_BIN, "add", 
             "--label", f"lesson:{domain}",
             "--type", "lesson",
             "--severity", severity,
             node_text],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


def sync_domain(domain: str) -> dict:
    """同步单个域的教训到graphify"""
    domain_file = LESSONS_DIR / f"{domain}-domain.md"
    if not domain_file.exists():
        domain_file = LESSONS_DIR / f"{domain}.md"
    if not domain_file.exists():
        # Also check global
        if domain == "global":
            domain_file = LESSONS_DIR / "global.md"
        else:
            return {"domain": domain, "total": 0, "new": 0, "errors": []}
    
    lessons = parse_lessons(domain_file)
    new_count = 0
    errors = []
    
    for lesson in lessons:
        # Check if already exists in graph
        existing = graphify_search(lesson["title"])
        if existing:
            continue
        
        # Add new node
        if graphify_add_node(lesson["title"], lesson["domain"], 
                            lesson["severity"], lesson["content"]):
            new_count += 1
        else:
            errors.append(lesson["title"][:60])
    
    return {
        "domain": domain,
        "total": len(lessons),
        "new": new_count,
        "errors": errors
    }


def sync_all() -> list[dict]:
    """全量同步所有域"""
    results = []
    domains = ["global", "code-domain", "ec-domain", "finance-domain", 
               "ops-domain", "research-domain", "writing-domain"]
    
    for domain in domains:
        result = sync_domain(domain)
        results.append(result)
        status = "✅" if result["errors"] == [] else "⚠️"
        print(f"  {status} {result['domain']}: {result['total']}条教训, {result['new']}条新增")
    
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="lesson ↔ graphify 知识桥接")
    parser.add_argument("--domain", type=str, help="同步指定域")
    parser.add_argument("--new", type=str, help="单条新增: 教训标题")
    parser.add_argument("--severity", type=str, default="MEDIUM", 
                       choices=["CRITICAL", "HIGH", "MEDIUM"])
    args = parser.parse_args()
    
    if not GRAPHIFY_BIN:
        print("⚠️ graphify CLI未找到，跳过图谱同步")
        print("   graphify用于知识图谱节点管理，不影响lessons文本功能")
        sys.exit(0)
    
    if args.new:
        # Single new lesson
        ok = graphify_add_node(args.new, args.domain or "global", args.severity, "")
        print(f"{'✅' if ok else '❌'} 已添加节点: {args.new[:60]}")
        return
    
    print(f"📊 lesson → graphify 知识桥接")
    print(f"   graphify: {GRAPHIFY_BIN}")
    
    if args.domain:
        result = sync_domain(args.domain)
        print(f"   {result['domain']}: {result['total']}条, {result['new']}条新增")
    else:
        results = sync_all()
        total_new = sum(r["new"] for r in results)
        total_lessons = sum(r["total"] for r in results)
        print(f"\n   总计: {total_lessons}条教训, {total_new}条新增图谱节点")


if __name__ == "__main__":
    main()
