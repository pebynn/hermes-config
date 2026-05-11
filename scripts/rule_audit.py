#!/usr/bin/env python3
"""
rule_audit.py v2 — SOUL.md规则遵守审计（仅通知，不惩罚）

每天10:00运行，扫描最近24h的session文件。
发现违规 → 记录+推送通知用户。不自动暂停cron。

Usage:
  python3 rule_audit.py              # 检查最近24h
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

HERMES_HOME = Path.home() / ".hermes"
SESSIONS_DIR = HERMES_HOME / "sessions"

RULES = [
    {
        "id": "no_forbidden_words",
        "desc": "禁用语",
        "patterns": [r"可以吗[？?]", r"怎么样[？?]", r"需要我[^做]", r"要不要[我你]"],
        "severity": "MEDIUM",
    },
    {
        "id": "no_self_calc",
        "desc": "禁止自行计算数据",
        "patterns": [r"close.*prev_close.*100", r"\(.*-.*\).*/.*prev", r"int\(lu\*\d+\)"],
        "severity": "CRITICAL",
    },
    {
        "id": "dead_list_mention",
        "desc": "提及死路",
        "patterns": [r"PDD开放平台API", r"ISV企业", r"雪球全自动发布"],
        "severity": "CRITICAL",
    },
]


def scan_sessions(hours=24):
    cutoff = datetime.now() - timedelta(hours=hours)
    violations = []
    
    for sf in sorted(SESSIONS_DIR.glob("session_*.json"), reverse=True):
        try:
            mtime = datetime.fromtimestamp(sf.stat().st_mtime)
            if mtime < cutoff:
                continue
        except OSError:
            continue
        
        try:
            with open(sf) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        
        messages = data.get("messages", [])
        assistant_text = " ".join(
            str(m.get("content", "")) for m in messages
            if m.get("role") == "assistant"
        )
        
        for rule in RULES:
            for pattern in rule["patterns"]:
                if re.search(pattern, assistant_text):
                    violations.append({
                        "session": sf.name,
                        "rule": rule["id"],
                        "desc": rule["desc"],
                        "severity": rule["severity"],
                    })
                    break
    
    return violations


def format_report(violations, hours):
    lines = []
    lines.append(f"## 📋 规则审计 ({hours}h)")
    
    if not violations:
        lines.append("✅ 无违规")
        return "\n".join(lines)
    
    lines.append(f"⚠️ 发现 {len(violations)} 次违规")
    severity_count = Counter(v["severity"] for v in violations)
    lines.append(f"   {' · '.join(f'{s}x{c}' for s,c in severity_count.most_common())}")
    
    lines.append("")
    lines.append("### 违规详情（仅通知，不暂停cron）")
    for v in violations[:5]:
        lines.append(f"  [{v['severity']}] {v['desc']}: {v['session'][:50]}")
    
    return "\n".join(lines)


def main():
    violations = scan_sessions()
    report = format_report(violations, 24)
    print(report)
    if violations:
        try:
            from notify import send
            send("规则审计违规", report)
        except Exception:
            pass
    sys.exit(1 if violations else 0)


if __name__ == "__main__":
    main()
