#!/usr/bin/env python3
"""Hermes Lesson Injector — 从教训知识库提取相关教训，注入子代理 context。

用法:
  python3 lesson_inject.py --domain writing-domain
  → 输出 domain 相关 + global 教训，按严重度排序

被主代理指令流水线 [1.5] 调用。
"""

import os, sys, re
from pathlib import Path
from datetime import datetime

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
LESSONS_DIR = HERMES_HOME / "lessons"

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}

def parse_lessons(filepath: Path) -> list:
    """解析 lesson 文件，提取教训条目。"""
    if not filepath.exists():
        return []
    
    content = filepath.read_text()
    lessons = []
    current_severity = "MEDIUM"
    current_title = ""
    current_body = []
    
    for line in content.split("\n"):
        line = line.rstrip()
        
        # 检测严重度标题
        if line.startswith("## 🔴") or "CRITICAL" in line:
            _flush(current_title, current_body, current_severity, lessons)
            current_severity = "CRITICAL"
            current_title = ""
            current_body = []
        elif line.startswith("## 🟠") or "HIGH" in line:
            _flush(current_title, current_body, current_severity, lessons)
            current_severity = "HIGH"
            current_title = ""
            current_body = []
        elif line.startswith("## 🟡") or "MEDIUM" in line:
            _flush(current_title, current_body, current_severity, lessons)
            current_severity = "MEDIUM"
            current_title = ""
            current_body = []
        elif line.startswith("### "):
            _flush(current_title, current_body, current_severity, lessons)
            current_title = line.replace("### ", "").strip()
            current_body = []
        elif line.startswith("## ") and not any(c in line for c in ["🔴","🟠","🟡"]):
            # 非严重度标题，跳过
            _flush(current_title, current_body, current_severity, lessons)
            current_severity = "MEDIUM"
            current_title = ""
            current_body = []
        elif current_title and line.strip():
            current_body.append(line.strip())
    
    _flush(current_title, current_body, current_severity, lessons)
    return lessons

def _flush(title, body, severity, lessons):
    if title:
        lessons.append({
            "title": title,
            "severity": severity,
            "body": "\n".join(body) if body else "",
            "sort_key": SEVERITY_ORDER.get(severity, 3)
        })

def inject(domain: str, keywords: list = None) -> str:
    """为特定 domain 注入教训，返回 formatted LESSON_BLOCK。"""
    all_lessons = []
    
    # 1. 加载 domain 特定教训
    domain_file = LESSONS_DIR / f"{domain}.md"
    all_lessons.extend(parse_lessons(domain_file))
    
    # 2. 加载 global 教训
    global_file = LESSONS_DIR / "global.md"
    all_lessons.extend(parse_lessons(global_file))
    
    if not all_lessons:
        return ""
    
    # 按严重度排序
    all_lessons.sort(key=lambda l: l["sort_key"])
    
    # 如果有关键词，做相关性过滤
    if keywords:
        filtered = []
        for l in all_lessons:
            score = sum(1 for kw in keywords if kw.lower() in (l["title"] + " " + l["body"]).lower())
            if score > 0 or l["severity"] == "CRITICAL":  # CRITICAL 不过滤
                filtered.append(l)
        all_lessons = filtered
    
    # 格式化输出
    severity_icons = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}
    
    lines = [
        "╔══════════════════════════════════════╗",
        "║  ⚠️  已知陷阱 - 本次任务必读        ║",
        "╚══════════════════════════════════════╝",
        ""
    ]
    
    for i, l in enumerate(all_lessons):
        icon = severity_icons.get(l["severity"], "📌")
        lines.append(f"  {icon} [{l['severity']}] {l['title']}")
        if l["body"]:
            for bline in l["body"].split("\n")[:3]:  # 最多3行
                if bline.strip():
                    lines.append(f"     {bline.strip()}")
        lines.append("")
    
    return "\n".join(lines)

def get_lesson_file(domain: str) -> Path:
    """获取域的教训文件路径。"""
    return LESSONS_DIR / f"{domain}.md"

def add_lesson(domain: str, severity: str, title: str, body: str = ""):
    """添加一条新教训。"""
    filepath = get_lesson_file(domain)
    if not filepath.exists():
        print(f"教训文件不存在: {filepath}")
        return False
    
    content = filepath.read_text()
    
    # 找到对应严重度的 section，在最后一个同严重度条目后插入
    severity_header = {"CRITICAL": "## 🔴 CRITICAL", "HIGH": "## 🟠 HIGH", "MEDIUM": "## 🟡 MEDIUM"}
    header = severity_header.get(severity, "## 🟡 MEDIUM")
    
    if header not in content:
        print(f"严重度 section 不存在: {header}")
        return False
    
    # 检查是否已存在同名教训
    if f"### {title}" in content:
        print(f"教训已存在: {title}")
        # 更新纠正次数
        content = _increment_correction_count(content, title)
        filepath.write_text(content)
        return True
    
    # 找到 section 结束位置插入
    lines = content.split("\n")
    insert_idx = None
    in_section = False
    for i, line in enumerate(lines):
        if line.strip() == header:
            in_section = True
        elif in_section and line.startswith("## ") and not line.startswith(header):
            insert_idx = i
            break
    
    if insert_idx is None:
        insert_idx = len(lines)
    
    new_entry = [
        "",
        f"### {title}",
    ]
    if body:
        new_entry.extend([f"- {bline}" for bline in body.split("\n") if bline.strip()])
    new_entry.append(f"- **纠正次数**: 1")
    new_entry.append(f"- **首次发现**: {datetime.now().strftime('%Y-%m-%d')}")
    
    for j, entry_line in enumerate(new_entry):
        lines.insert(insert_idx + j, entry_line)
    
    filepath.write_text("\n".join(lines))
    
    # Post-hook: 铁律级教训同步写 memory user
    if severity == "CRITICAL":
        print(f"  ↳ 建议: memory(action='add', target='user') 铁律: {title[:40]}")
    return True

def _increment_correction_count(content: str, title: str) -> str:
    """增加教训的纠正计数。"""
    pattern = rf"(### {re.escape(title)}.*?\n.*?\*\*纠正次数\*\*: )(\d+)"
    
    def replacer(m):
        count = int(m.group(2)) + 1
        return f"{m.group(1)}{count}"
    
    new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)
    
    if new_content != content:
        # 检查是否需要升格 (≥3次 → 建议升格)
        m = re.search(pattern, new_content, re.DOTALL)
        if m and int(m.group(2)) >= 3:
            print(f"⚠️  教训 '{title}' 已被纠正 {m.group(2)} 次 → 建议升格为域 SOUL.md 硬约束")
    
    return new_content

# === CLI ===
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hermes Lesson Injector")
    sub = parser.add_subparsers(dest="action")
    
    inject_p = sub.add_parser("inject", help="注入教训到 context")
    inject_p.add_argument("--domain", required=True)
    inject_p.add_argument("--keywords", nargs="*", help="过滤关键词")
    
    add_p = sub.add_parser("add", help="添加教训")
    add_p.add_argument("--domain", required=True)
    add_p.add_argument("--severity", choices=["CRITICAL","HIGH","MEDIUM"], default="MEDIUM")
    add_p.add_argument("--title", required=True)
    add_p.add_argument("--body", default="")
    
    list_p = sub.add_parser("list", help="列出域的所有教训")
    list_p.add_argument("--domain", required=True)
    
    args = parser.parse_args()
    
    if args.action == "inject":
        result = inject(args.domain, args.keywords)
        print(result)
    elif args.action == "add":
        ok = add_lesson(args.domain, args.severity, args.title, args.body)
        print(f"添加教训: {'OK' if ok else 'FAILED'}")
    elif args.action == "list":
        filepath = get_lesson_file(args.domain)
        if filepath.exists():
            print(filepath.read_text())
        else:
            print(f"教训文件不存在: {filepath}")
    else:
        parser.print_help()
