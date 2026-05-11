#!/usr/bin/env python3
"""
Hermes Cron 失败看门狗 — 监控 errors.log 中最近30分钟的 ERROR，过滤噪音，推送真实错误到 QQ Bot。

设计：
- 纯 Python stdlib，无 LLM 依赖，适合 no_agent=true cron 模式
- 只提取最近30分钟内的 ERROR 级别日志
- 过滤已知噪音（asyncio 任务销毁、限流、连接拒绝等）
- 同一条错误30分钟内不重复告警（基于指纹哈希）
- 有真实错误 → print 摘要到 stdout（QQ Bot 收取）+ 调用 notify.py 写队列
- 无新错误 → 静默退出 (exit 0)
"""

import json
import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import traceback

# === 路径配置 ===
HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
ERRORS_LOG = HERMES_HOME / "logs" / "errors.log"
STATE_FILE = HERMES_HOME / "data" / "watchdog_state.json"
NOTIFY_SCRIPT = HERMES_HOME / "scripts" / "notify.py"

WINDOW_MINUTES = 30
DEDUP_MINUTES = 30

# === 噪音模式（子串匹配） ===
NOISE_PATTERNS = [
    "Task was destroyed but it is pending",
    "Task exception was never retrieved",
    "Unhandled error in exception handler",       # asyncio 内部异常处理器噪音
    "Connection refused",                          # browser CDP / 网络连接被拒
    "Rate limit reached",                          # 会话摘要限流
    "rate limited",                                # Weixin iLink 硬限流
    "Temporary failure in name resolution",        # QQBot DNS 解析失败
    "Session timed out",                           # 会话超时
    "cannot schedule new futures after interpreter shutdown",  # Hermes 关闭时正常现象
    "aclose(): asynchronous generator is already running",     # asyncio 生成器噪音
    "got Future attached to a different loop",     # asyncio 事件循环噪音
    "unhandled exception during asyncio.run() shutdown",  # gateway 重启时正常
    "Unclosed client session",                      # gateway 重启时客户端残留
]


def parse_timestamp(line: str) -> datetime | None:
    """从日志行开头提取时间戳: YYYY-MM-DD HH:MM:SS,mmm"""
    m = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3}", line)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            traceback.print_exc()
            pass
    return None


def is_noise(block: str) -> bool:
    """判断错误块是否为已知噪音"""
    for pattern in NOISE_PATTERNS:
        if pattern in block:
            return True
    return False


def fingerprint(error_line: str) -> str:
    """生成错误指纹（SHA256 前16位），用于去重"""
    # 去掉时间戳部分，只对消息内容做指纹
    m = re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ERROR (.*)", error_line)
    msg = m.group(1).strip() if m else error_line.strip()
    # 截断到200字符，避免 traceback 污染指纹
    return hashlib.sha256(msg[:200].encode()).hexdigest()[:16]


def extract_error_blocks(log_path: Path, since: datetime) -> list[tuple[str, datetime]]:
    """
    从日志文件中提取最近 window 内的 ERROR 块。
    返回 [(error_block_text, timestamp), ...]
    """
    if not log_path.exists():
        return []

    blocks: list[tuple[str, datetime]] = []
    current_block_lines: list[str] = []
    current_ts: datetime | None = None

    with open(log_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            # 检测是否为新行的开始（带时间戳）
            ts = parse_timestamp(line)
            if ts is not None:
                # 保存上一个错误块
                if current_ts is not None and current_block_lines:
                    blocks.append(("\n".join(current_block_lines), current_ts))
                # 开始新行
                current_block_lines = [line]
                current_ts = ts
            else:
                # 续行（traceback、多行消息等）
                if current_block_lines:
                    current_block_lines.append(line)

        # 最后一个块
        if current_ts is not None and current_block_lines:
            blocks.append(("\n".join(current_block_lines), current_ts))

    # 筛选 ERROR 级别且在时间窗口内
    error_blocks = []
    for block, ts in blocks:
        if " ERROR " not in block.split("\n")[0]:
            continue
        if ts >= since:
            error_blocks.append((block, ts))

    return error_blocks


def load_state() -> dict:
    """加载状态文件"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_check": None, "alerted_fingerprints": {}}


def save_state(state: dict):
    """保存状态文件"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def prune_old_fingerprints(fingerprints: dict, now: datetime):
    """清理超过去重窗口的指纹"""
    cutoff = now - timedelta(minutes=DEDUP_MINUTES)
    return {
        fp: ts for fp, ts in fingerprints.items()
        if datetime.fromisoformat(ts) > cutoff
    }


def main():
    now = datetime.now()
    since = now - timedelta(minutes=WINDOW_MINUTES)
    now_iso = now.isoformat()

    # 加载状态
    state = load_state()
    alerted = prune_old_fingerprints(state.get("alerted_fingerprints", {}), now)

    # 提取错误块
    error_blocks = extract_error_blocks(ERRORS_LOG, since)

    # 过滤噪音 & 去重
    real_errors = []
    for block, ts in error_blocks:
        if is_noise(block):
            continue

        first_line = block.split("\n")[0]
        fp = fingerprint(first_line)

        # 检查是否在去重窗口内已告警
        if fp in alerted:
            alerted_time = datetime.fromisoformat(alerted[fp])
            if now - alerted_time < timedelta(minutes=DEDUP_MINUTES):
                continue

        real_errors.append((block, ts, fp))

    # 更新状态
    state["last_check"] = now_iso
    save_state(state)

    # 无真实错误 → 静默退出
    if not real_errors:
        return 0

    # 构建通知内容
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"🔔 Cron 异常检测 | {timestamp_str}",
        f"最近 {WINDOW_MINUTES} 分钟内发现 {len(real_errors)} 条真实错误：",
        "",
    ]

    for i, (block, ts, fp) in enumerate(real_errors, 1):
        err_time = ts.strftime("%H:%M:%S")
        first_line = block.split("\n")[0]
        # 截取消息部分（去掉时间戳前缀）
        m = re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ERROR (.*)", first_line)
        msg = m.group(1).strip()[:200] if m else first_line[:200]

        lines.append(f"[{i}] {err_time} {msg}")

        # 标记已告警
        alerted[fp] = now_iso

    summary = "\n".join(lines)

    # 打印到 stdout → cron no_agent 模式会投递到 QQ Bot
    print(summary)

    # 同时调用 notify.py 写入通知队列
    body_parts = []
    for b, _, _ in real_errors:
        m = re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ERROR (.*)", b.split("\n")[0])
        if m:
            body_parts.append(m.group(1).strip()[:300])
    body_one_liner = " | ".join(body_parts) if body_parts else "未知错误"

    # 单条时用具体消息，多条时用摘要
    if len(real_errors) == 1:
        notify_body = body_one_liner
    else:
        notify_body = f"{len(real_errors)}条错误:\n{body_one_liner}"

    try:
        from notify import send
        send("Cron异常检测", notify_body)
    except Exception:
        traceback.print_exc()
        pass

    # 保存更新后的指纹
    state["alerted_fingerprints"] = alerted
    state["last_check"] = now_iso
    save_state(state)

    return 0


if __name__ == "__main__":
    sys.exit(main())
