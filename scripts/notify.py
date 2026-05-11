#!/usr/bin/env python3
"""Hermes 统一通知模块 — 所有脚本的唯一 QQ Bot 通知入口

设计：写文件到 ~/.hermes/notify_queue/ → pipeline_runner(fc7f76d16dd3)每30min扫描投递

用法（Python API）:
    from notify import send
    send("复盘文章已生成", "2026-05-11 每日复盘 → 公众号草稿箱")

用法（Shell）:
    python3 ~/.hermes/scripts/notify.py "标题" "正文"

所有 writing-domain 脚本必须通过此模块发送 QQ 通知，禁止各自实现。
"""

import os
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
QUEUE_DIR = HERMES_HOME / "notify_queue"
QUEUE_DIR.mkdir(parents=True, exist_ok=True)


def send(title: str, body: str = "", priority: str = "P1") -> bool:
    """发送 QQ Bot 通知（写入文件队列，由 pipeline_runner 投递）

    Args:
        title: 通知标题
        body:  通知正文
        priority: P0(紧急)/P1(重要)/P2(提示)/P3(仅摘要)
    """
    try:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "priority": priority,
            "title": title,
            "body": body,
        }
        out = QUEUE_DIR / f"{ts}.json"
        out.write_text(json.dumps(entry, ensure_ascii=False))
        return True
    except Exception:
        return False


def article_published(article_type: str, date_str: str, extra: str = "") -> bool:
    """便捷函数：文章发布通知

    Args:
        article_type: "每日复盘" | "周总结" | "早报" | "科普" | "短内容" | "量化周报"
        date_str:    日期 YYYY-MM-DD
        extra:       额外信息（如文章字数）
    """
    type_icon = {
        "每日复盘": "📊", "周总结": "📈", "早报": "🌅",
        "科普": "📖", "短内容": "📱", "量化周报": "🔬",
    }
    icon = type_icon.get(article_type, "📌")
    title = f"{icon} {article_type}已生成"
    body = f"{date_str} {article_type}"
    if extra:
        body += f" | {extra}"
    body += "\n→ 公众号草稿箱待审核发布"
    return send(title, body)


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) >= 3:
        send(sys.argv[1], sys.argv[2])
        print("OK")
    elif len(sys.argv) == 2:
        send(sys.argv[1])
        print("OK")
    else:
        print("用法: python3 notify.py '标题' ['正文']")
        sys.exit(1)
