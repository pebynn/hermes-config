#!/usr/bin/env python3
"""
evoclaw_degradation_detect.py — EvoClaw-inspired B/D layer degradation detection

Monitors B-layer (已知陷阱 injection) and D-layer ([LESSONS] recovery) rates
from kanban.db over a 7-day window. Implements two alert thresholds:

  P1 Warning: 3+ consecutive days of metric decline
  P0 Alert:   >50% drop in any single metric vs 5-day baseline

Usage:
  python3 evoclaw_degradation_detect.py          # daily cron run
  python3 evoclaw_degradation_detect.py --json   # JSON output mode
  python3 evoclaw_degradation_detect.py --dry-run # no alerts, just print

Exit codes:
  0 — OK (no degradation or dry-run)
  1 — P1 warning(s) sent
  2 — P0 alert(s) sent
  3 — Error (DB missing, etc.)

Cron: no_agent=true, zero-token, pure stdlib + sqlite3.

Reference: EvoClaw benchmark (arXiv 2603.13428) — agent performance can
degrade from >80% to 38% under continuous evolution.
"""

import sys
import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

def _resolve_hermes_root():
    """Resolve the actual .hermes root, handling profile-sandboxed HOME."""
    hermes_home = os.environ.get("HERMES_HOME", "")
    if hermes_home and "/profiles/" in hermes_home:
        # HERMES_HOME points to profiles/<name> — go up 2 levels to .hermes root
        return Path(hermes_home).parent.parent

    # Fallback 1: expanduser (works outside sandbox)
    expanded = Path(os.path.expanduser("~/.hermes"))
    if (expanded / "kanban.db").exists():
        return expanded

    # Fallback 2: absolute path (cron/container without env vars)
    abs_path = Path("/home/pebynn/.hermes")
    if (abs_path / "kanban.db").exists():
        return abs_path

    # Last resort — return expanded path even if it doesn't exist
    # (error will surface later with a clear message)
    return expanded

HERMES_ROOT = _resolve_hermes_root()
KANBAN_DB = HERMES_ROOT / "kanban.db"
HISTORY_FILE = HERMES_ROOT / "metrics" / "evoclaw_history.json"
LOOKBACK_DAYS = 7
BASELINE_WINDOW = 5      # days -7 through -3 for baseline
MIN_TASKS_FOR_ALERT = 3  # skip alerts if fewer than N tasks today
CONSECUTIVE_DECLINE = 3  # N days of monotonic decline triggers P1

# Alert thresholds
P0_DROP_PCT = 0.50  # >50% drop vs baseline


# ──────────────────────────────────────────────
# Core: Daily B/D Rate Computation
# ──────────────────────────────────────────────

def compute_daily_bd_rates(db_path=None, days=LOOKBACK_DAYS):
    """Compute per-day B/D injection rates from kanban.db.

    Returns list of dicts, most recent first (index 0 = today):
      [{date, total, done, b_count, b_rate, d_count, d_rate}, ...]
    """
    db = Path(db_path) if db_path else KANBAN_DB
    if not db.exists():
        return []

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row

    results = []
    now = datetime.now()

    for day_offset in range(days):
        day_start = (now - timedelta(days=day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_start_ts = int(day_start.timestamp())
        day_end_ts = int(day_end.timestamp())
        date_str = day_start.strftime("%Y-%m-%d")

        # Total tasks created on this day
        cur = conn.execute(
            "SELECT count(*) FROM tasks WHERE created_at >= ? AND created_at < ?",
            (day_start_ts, day_end_ts))
        total = cur.fetchone()[0]

        # B-layer: tasks with "已知陷阱" in body
        cur = conn.execute(
            "SELECT count(*) FROM tasks "
            "WHERE created_at >= ? AND created_at < ? AND body LIKE '%已知陷阱%'",
            (day_start_ts, day_end_ts))
        b_count = cur.fetchone()[0]

        # Completed tasks on this day (by task creation date)
        cur = conn.execute(
            "SELECT count(DISTINCT r.task_id) FROM task_runs r "
            "JOIN tasks t ON t.id = r.task_id "
            "WHERE t.created_at >= ? AND t.created_at < ? AND r.outcome = 'completed'",
            (day_start_ts, day_end_ts))
        done = cur.fetchone()[0]

        # D-layer: completed tasks with [LESSONS] in summary
        cur = conn.execute(
            "SELECT count(DISTINCT r.task_id) FROM task_runs r "
            "JOIN tasks t ON t.id = r.task_id "
            "WHERE t.created_at >= ? AND t.created_at < ? "
            "AND r.outcome = 'completed' AND r.summary LIKE '%[LESSONS]%'",
            (day_start_ts, day_end_ts))
        d_count = cur.fetchone()[0]

        b_rate = b_count / total if total > 0 else 0.0
        d_rate = d_count / done if done > 0 else 0.0

        results.append({
            "date": date_str,
            "total": total,
            "done": done,
            "b_count": b_count,
            "b_rate": round(b_rate, 4),
            "d_count": d_count,
            "d_rate": round(d_rate, 4),
        })

    conn.close()
    return results


# ──────────────────────────────────────────────
# Core: Degradation Detection
# ──────────────────────────────────────────────

def check_degradation(today, history):
    """Check for degradation patterns in B/D rates.

    Args:
        today: dict with {date, b_rate, d_rate, total, done}
        history: list of dicts, oldest first

    Returns:
        list of alert dicts: [{priority, title, body}]
    """
    alerts = []

    # Skip if too few tasks today
    if today["total"] < MIN_TASKS_FOR_ALERT:
        return alerts

    # Build time series: history + today
    full_series = list(history) + [today]

    # ── Check 1: 3+ consecutive days of decline ──

    for metric, label_cn, label_en in [
        ("b_rate", "B层注入率", "B_layer"),
        ("d_rate", "D层回收率", "D_layer"),
    ]:
        values = [d[metric] for d in full_series]
        # Find the longest consecutive decline streak ending at today
        streak = 1
        for i in range(len(values) - 1, 0, -1):
            if values[i] < values[i - 1]:
                streak += 1
            else:
                break

        if streak >= CONSECUTIVE_DECLINE:
            # Format the declining values
            decline_vals = values[-(streak):]
            dates = [full_series[-(streak) + j]["date"] for j in range(streak)]
            trend_str = " → ".join(
                f"{v:.0%}" for v in decline_vals
            )
            alerts.append({
                "priority": "P1",
                "title": f"⚠️ B/D层退化警告 — {label_cn}连续{streak}天下降",
                "body": (
                    f"{label_cn}: {trend_str}\n"
                    f"时段: {dates[0]} → {dates[-1]}\n"
                    f"当前值: {decline_vals[-1]:.1%}\n"
                    f"触发阈值: 连续{CONSECUTIVE_DECLINE}天下降"
                ),
            })

    # ── Check 2: >50% drop vs 5-day baseline ──

    # Baseline: average of oldest LOOKBACK_DAYS-BASELINE_WINDOW entries in history
    # (first N entries before the most recent 2 days)
    if len(history) >= BASELINE_WINDOW:
        # Use the first BASELINE_WINDOW entries of history (oldest, days -7 to -3)
        baseline_entries = history[:BASELINE_WINDOW]

        for metric, label_cn, label_en in [
            ("b_rate", "B层注入率", "B_layer"),
            ("d_rate", "D层回收率", "D_layer"),
        ]:
            baseline_avg = sum(d[metric] for d in baseline_entries) / len(baseline_entries)
            current = today[metric]

            if baseline_avg > 0 and current < baseline_avg * (1 - P0_DROP_PCT):
                drop_pct = (1 - current / baseline_avg) * 100
                alerts.append({
                    "priority": "P0",
                    "title": f"🚨 B/D层P0告警 — {label_cn}骤降>{P0_DROP_PCT:.0%}",
                    "body": (
                        f"{label_cn} today: {current:.1%} vs 基线({BASELINE_WINDOW}d avg): {baseline_avg:.1%}\n"
                        f"跌幅: {drop_pct:.1f}%\n"
                        f"日期: {today['date']}\n"
                        f"任务数: {today['total']} (完成: {today['done']})\n"
                        f"触发阈值: >{P0_DROP_PCT:.0%}跌幅"
                    ),
                })

    return alerts


# ──────────────────────────────────────────────
# History Persistence
# ──────────────────────────────────────────────

def load_history(path=None):
    """Load historical snapshots from JSON file.

    Returns list of dicts, oldest first. Empty list on missing/corrupt file.
    """
    p = Path(path) if path else HISTORY_FILE
    if not p.exists():
        return []

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, ValueError, OSError):
        pass

    return []


def save_history(snapshot, path=None):
    """Append snapshot to history file. Keeps at most 90 days of data."""
    p = Path(path) if path else HISTORY_FILE
    p.parent.mkdir(parents=True, exist_ok=True)

    history = load_history(p)

    # Avoid duplicate entries for the same date (idempotent)
    history = [h for h in history if h.get("date") != snapshot.get("date")]
    history.append(snapshot)

    # Trim to last 90 days
    if len(history) > 90:
        history = history[-90:]

    p.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n")


# ──────────────────────────────────────────────
# Notify Integration
# ──────────────────────────────────────────────

def send_alert(alert):
    """Send alert via notify.py queue."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from notify import send
        return send(alert["title"], alert["body"], priority=alert["priority"])
    except ImportError:
        print(f"[FALLBACK] Would notify: [{alert['priority']}] {alert['title']}", file=sys.stderr)
        return False


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv
    json_out = "--json" in sys.argv

    # Step 1: Compute today's rates + 6 prior days
    rates = compute_daily_bd_rates()
    if not rates:
        msg = "ERROR: kanban.db not found or empty"
        print(msg, file=sys.stderr)
        sys.exit(3)

    today = rates[0]    # most recent
    prior = rates[1:]   # days -1 through -6
    # Reverse prior so oldest is first
    prior.reverse()

    # Step 2: Check for degradation
    alerts = check_degradation(today, prior)

    # Step 3: Save to history
    save_history(today)

    # Step 4: Output and alert
    if json_out:
        output = {
            "today": today,
            "prior_days": prior,
            "alerts": alerts,
            "summary": f"B:{today['b_rate']:.0%} D:{today['d_rate']:.0%} "
                       f"({'⚠️' if alerts else '✅'})"
        }
        print(json.dumps(output, ensure_ascii=False))
    else:
        print(f"EvoClaw B/D Degradation Check — {today['date']}")
        print(f"  Today: {today['total']} tasks, {today['done']} completed")
        print(f"  B_rate: {today['b_rate']:.1%} ({today['b_count']}/{today['total']})")
        print(f"  D_rate: {today['d_rate']:.1%} ({today['d_count']}/{today['done']})")

        if alerts:
            for a in alerts:
                print(f"\n  [{a['priority']}] {a['title']}")
        else:
            print(f"\n  ✅ No degradation detected")

    # Step 5: Send alerts
    if not dry_run:
        sent = 0
        for alert in alerts:
            if send_alert(alert):
                sent += 1
            elif not json_out:
                print(f"  [NOTIFY] {alert['priority']}: {alert['title']}")

        if sent and not json_out:
            print(f"\n  Sent {sent} alert(s) via notify.py")

    # Exit codes
    has_p0 = any(a["priority"] == "P0" for a in alerts)
    has_p1 = any(a["priority"] == "P1" for a in alerts)

    if dry_run:
        sys.exit(0)
    elif has_p0:
        sys.exit(2)
    elif has_p1:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()


# [LESSONS]
# - level: 🟢 INFO
#   domain: code-domain
#   content: EvoClaw degradation detection implemented — monitors B/D rates from kanban.db with 7-day window, P1 warning for 3+ consecutive day decline, P0 alert for >50% drop vs 5-day baseline. Zero-token cron compatible.
#   context: Implemented per t_457f1d86 task. Design decision: direct kanban.db SQLite query rather than parsing audit_bd_layer.py output, since audit_bd_layer only prints stdout and doesn't persist. History stored in ~/.hermes/metrics/evoclaw_history.json for trend stability across runs.
# - level: 🟡 WARNING
#   domain: code-domain
#   content: EvoClaw baseline definition nuanced — using average of days -7..-3 (5-day window) as baseline excludes yesterday (may be start of decline) and today. Need to validate this window size empirically over weeks of real data.
#   context: During design, considered fixed-baseline vs rolling-window. Rolling window captures natural drift but a too-short window may miss the degradation. 5-day chosen as compromise between stability and recency.
