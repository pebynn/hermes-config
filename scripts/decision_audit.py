#!/usr/bin/env python3
"""
decision_audit.py — 决策矩阵违规日终审计

扫描 decision_violations.log，统计当日违规次数。
>0 条 → 输出报告（QQ Bot 推送）。
=0 条 → 静默。

Usage:
  python3 decision_audit.py
"""

import os, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
VIOLATION_LOG = HERMES_HOME / "logs" / "decision_violations.log"
TZ = timezone(timedelta(hours=8))


def main():
    if not VIOLATION_LOG.exists():
        sys.exit(0)  # 无日志 = 无违规 = 静默

    today = datetime.now(TZ).strftime("%Y-%m-%d")
    lines = VIOLATION_LOG.read_text().split("\n")

    today_violations = []
    for line in lines:
        if line.startswith(f"[{today}"):
            today_violations.append(line)

    if not today_violations:
        sys.exit(0)

    # 统计
    count = len([l for l in today_violations if l.strip() and not l.startswith("  ")])
    sessions = set()
    patterns = {}
    for l in today_violations:
        if "session=" in l:
            sid = l.split("session=")[1].split(" ")[0]
            sessions.add(sid)
        if "|" in l:
            for part in l.split("|")[1:]:
                p = part.strip().split(" ")[0] if " " in part.strip() else part.strip()
                if p:
                    patterns[p] = patterns.get(p, 0) + 1

    print(f"⚠️ 决策矩阵违规日报 {today}")
    print(f"   违规次数: {count}")
    print(f"   涉及会话: {len(sessions)}")
    print(f"   高频模式: {dict(sorted(patterns.items(), key=lambda x: -x[1])[:3])}")


if __name__ == "__main__":
    main()
