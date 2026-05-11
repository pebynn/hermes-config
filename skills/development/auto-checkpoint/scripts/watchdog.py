#!/usr/bin/env python3
"""Check active Hermes session length and notify if too long.

Usage: python3 ~/.hermes/skills/development/auto-checkpoint/scripts/watchdog.py

Designed to run as cron job (e.g., every 30min).
If current session exceeds threshold, writes checkpoint and sends WeChat notification.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

SESSIONS_DIR = Path.home() / ".hermes" / "sessions"
CHECKPOINT_DIR = Path.home() / ".hermes" / "checkpoints"
TURN_THRESHOLD = 50  # notify at 50 turns
FORCE_THRESHOLD = 80  # urgent at 80 turns
MAX_SESSION_AGE_HOURS = 6  # ignore sessions older than this


def find_active_session():
    """Find the most recent session file that's still active."""
    if not SESSIONS_DIR.exists():
        return None

    jsonl_files = sorted(SESSIONS_DIR.glob("*.jsonl"), key=os.path.getmtime, reverse=True)
    if not jsonl_files:
        return None

    latest = jsonl_files[0]
    age_hours = (datetime.now().timestamp() - os.path.getmtime(latest)) / 3600

    if age_hours > MAX_SESSION_AGE_HOURS:
        return None  # stale session

    return latest


def count_turns(session_path):
    """Count user/assistant round-trips."""
    user_count = 0
    try:
        with open(session_path) as f:
            for line in f:
                try:
                    msg = json.loads(line)
                    if msg.get("role") == "user":
                        user_count += 1
                except json.JSONDecodeError:
                    pass
    except Exception:
        return 0
    return user_count


def extract_last_user_message(session_path):
    """Get the last user message for context."""
    last_msg = ""
    try:
        with open(session_path) as f:
            for line in f:
                try:
                    msg = json.loads(line)
                    if msg.get("role") == "user":
                        last_msg = msg.get("content", "")
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return last_msg[:200]  # truncate


def generate_checkpoint(session_path, turns):
    """Generate summary checkpoint file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    checkpoint_file = CHECKPOINT_DIR / f"session_{timestamp}.md"
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    last_msg = extract_last_user_message(session_path)

    content = f"""# Session Checkpoint — {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 状态
{turns} 轮对话，session: {session_path.name}

## 最后上下文
{last_msg}

## 待继续
- [ ] （请在新会话中补充待办）

## 恢复指令
直接粘贴此文件内容到 /new 后的新会话。
"""
    checkpoint_file.write_text(content)
    return checkpoint_file


def notify(turns, checkpoint_path):
    """Print notification (cron will deliver this via WeChat)."""
    if turns >= FORCE_THRESHOLD:
        level = "⚠️ 紧急"
    else:
        level = "📊 提醒"

    print(f"{level}: Hermes 会话已达 {turns} 轮")
    print(f"Checkpoint: {checkpoint_path}")
    print(f"建议: 在终端执行 /new → 粘贴 checkpoint 文件内容 → 继续")


def main():
    session_path = find_active_session()

    if session_path is None:
        print("No active session found (idle or no sessions)")
        sys.exit(0)

    turns = count_turns(session_path)

    if turns < TURN_THRESHOLD:
        print(f"Session OK: {turns} turns (threshold: {TURN_THRESHOLD})")
        sys.exit(0)

    checkpoint_path = generate_checkpoint(session_path, turns)
    notify(turns, checkpoint_path)


if __name__ == "__main__":
    main()
