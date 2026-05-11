"""
decision-guard hook — 扫描 agent:end 事件，检测决策矩阵违规。

违规模式：
1. L1/L2 动作后跟问号（"要不要/可以吗/怎么样/需要我"）
2. 向用户征求已分类为 L1/L2 的许可

检测到违规 → 写入 violation log + 递增计数器。
单次会话 ≥3 次 → QQ Bot 通知。
"""

import json, os, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
VIOLATION_LOG = HERMES_HOME / "logs" / "decision_violations.log"
STATE_FILE = HERMES_HOME / "data" / "decision_guard_state.json"
TZ = timezone(timedelta(hours=8))

# 违规模式
VIOLATION_PATTERNS = [
    (r"[？?].*要.*配|要不要|可以吗|怎么样.*配|需要我.*做", "L2征求许可"),
    (r"现在.*要做.*[？?]|接下来.*[？?]", "L2动作后加问号"),
    (r"是否.*[？?]|需.*确认.*[？?]", "L2征求意见"),
    (r"我先.*[？?]|让我.*[？?]", "L2征求意见"),
]


def scan_message(text: str) -> list[dict]:
    """扫描文本，返回违规列表"""
    violations = []
    for pattern, label in VIOLATION_PATTERNS:
        if re.search(pattern, text):
            violations.append({"pattern": label, "matched": pattern})
    return violations


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"total_violations": 0, "session_violations": {}, "last_notify": None}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


async def handle(event_type: str, context: dict):
    """Gateway hook handler — 扫描 agent:end 事件的 response 字段"""
    response = context.get("response", "")
    if not response:
        return

    violations = scan_message(response)
    if not violations:
        return

    session_id = context.get("session_id", "unknown")
    platform = context.get("platform", "unknown")
    now = datetime.now(TZ)

    # 写日志
    VIOLATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(VIOLATION_LOG, "a") as f:
        f.write(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] session={session_id} ")
        for v in violations:
            f.write(f"| {v['pattern']} ")
        f.write(f"\n  原文(前80字): {response[:80]}\n")

    # 更新状态
    state = load_state()
    state["total_violations"] += len(violations)
    sess = state["session_violations"].get(session_id, 0)
    sess += len(violations)
    state["session_violations"][session_id] = sess
    save_state(state)

    # 阈值通知（同会话 ≥3 次）
    if sess >= 3:
        last = state.get("last_notify", "")
        if last != session_id:  # 同会话不重复通知
            state["last_notify"] = session_id
            save_state(state)
            # 写入通知队列
            notify_queue = HERMES_HOME / "notify_queue" / "decision_guard.json"
            notify_queue.parent.mkdir(parents=True, exist_ok=True)
            notify_queue.write_text(json.dumps({
                "event": "decision_violation",
                "session_id": session_id,
                "count": sess,
                "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            }, ensure_ascii=False))
