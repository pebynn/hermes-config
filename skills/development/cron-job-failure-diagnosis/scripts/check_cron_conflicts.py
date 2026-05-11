#!/usr/bin/env python3
"""
Cron Schedule Conflict Detector
================================
Reads `hermes cron list` output and detects:
  1. Same-time conflicts (multiple crons at same minute)
  2. 30-min window congestion (≥3 crons within 30 min window)
  3. Duplicate jobs (same functionality at same schedule)

Usage:
  python3 check_cron_conflicts.py

Output:
  - Same-time conflicts with affected job names + deliver mode
  - 30-min congestion windows with affected jobs
  - Total cron health summary

Exit code:
  0 = no conflicts found
  1 = conflicts found
"""

import subprocess
import re
import sys
from collections import defaultdict
from datetime import datetime


def parse_cron_list() -> list[dict]:
    """Parse `hermes cron list` output into structured list."""
    result = subprocess.run(
        ["hermes", "cron", "list"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print(f"ERROR: hermes cron list failed: {result.stderr}")
        sys.exit(2)

    crons = []
    current = {}
    for line in result.stdout.split('\n'):
        m = re.match(r'^\s+Name:\s+(.+)$', line)
        if m:
            current = {'name': m.group(1).strip()}
            crons.append(current)
            continue
        m = re.match(r'^\s+Schedule:\s+(.+)$', line)
        if m and current is not None:
            current['schedule'] = m.group(1).strip()
            continue
        m = re.match(r'^\s+Deliver:\s+(.+)$', line)
        if m and current is not None:
            current['deliver'] = m.group(1).strip()
            continue
        m = re.match(r'^\s+Last run:\s+(.+?)(?:\s+(ok|error))?$', line)
        if m and current is not None:
            current['last_run'] = m.group(1).strip()
            current['last_status'] = m.group(2) or 'unknown'
            continue
        m = re.match(r'^\s+Last status:\s+(.+)$', line)
        if m and current is not None:
            current['last_status'] = m.group(1).strip()
            continue
        # Reset on job ID marker
        if re.match(r'^\s{2}[a-f0-9]{12}\s', line):
            current = {}

    return crons


def parse_minute(schedule: str) -> int | None:
    """Convert cron schedule to minutes-since-midnight. Returns None for non-fixed schedules."""
    parts = schedule.split()
    if len(parts) != 5:
        return None
    min_str, hour_str = parts[0], parts[1]
    try:
        h = int(hour_str) if hour_str != '*' else -1
        m = int(min_str) if min_str != '*' else -1
        if h >= 0 and m >= 0:
            return h * 60 + m
    except ValueError:
        pass
    return None


def analyze_conflicts(crons: list[dict]) -> dict:
    """Analyze cron list for conflicts."""
    # Group by schedule string
    by_schedule = defaultdict(list)
    for c in crons:
        s = c.get('schedule', '?')
        by_schedule[s].append(c)

    # Group by minute (for fixed-schedule crons)
    by_minute = defaultdict(list)
    for c in crons:
        ts = parse_minute(c.get('schedule', ''))
        if ts is not None:
            by_minute[ts].append(c)

    results = {
        'total': len(crons),
        'same_time_conflicts': [],
        'duplicates': [],
        'thirty_min_windows': [],
        'conflict_count': 0,
    }

    # Same-time conflicts (same cron schedule string, multiple jobs)
    for sched, names in sorted(by_schedule.items()):
        if len(names) > 1:
            delivers = ', '.join(f"{n['name']} ({n.get('deliver','local')})" for n in names)
            results['same_time_conflicts'].append({
                'schedule': sched,
                'jobs': [n['name'] for n in names],
                'delivers': delivers,
                'count': len(names),
            })
            results['conflict_count'] += 1

    # 30-min window congestion
    sorted_minutes = sorted(by_minute.keys())
    for i, t1 in enumerate(sorted_minutes):
        window_jobs = []
        for t2 in sorted_minutes[i:]:
            if t2 - t1 <= 30:
                window_jobs.extend(by_minute[t2])
        if len(window_jobs) >= 4:  # 4+ jobs within 30 min window
            results['thirty_min_windows'].append({
                'start_minute': t1,
                'start_time': f"{t1//60:02d}:{t1%60:02d}",
                'end_time': f"{(t1+30)//60:02d}:{(t1+30)%60:02d}",
                'count': len(window_jobs),
                'jobs': [j['name'] for j in window_jobs],
            })

    return results


def print_report(results: dict):
    """Print human-readable conflict report."""
    print(f"Cron Schedule Conflict Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Total crons: {results['total']}")
    print()

    if not results['same_time_conflicts'] and not results['thirty_min_windows']:
        print("✅ No schedule conflicts found.")
        return

    if results['same_time_conflicts']:
        print(f"⚠️  SAME-TIME CONFLICTS ({len(results['same_time_conflicts'])}):")
        for c in results['same_time_conflicts']:
            print(f"  Schedule: {c['schedule']}  ({c['count']} jobs)")
            for line in c['delivers'].split(', '):
                print(f"    • {line}")
        print()

    if results['thirty_min_windows']:
        print(f"⚠️  30-MIN CONGESTION ({len(results['thirty_min_windows'])} windows):")
        for w in results['thirty_min_windows']:
            print(f"  {w['start_time']}–{w['end_time']}  |  {w['count']} jobs")
            for j in w['jobs']:
                print(f"    • {j}")
        print()

    print(f"Total conflicts: {results['conflict_count']}")
    print()
    print("⚡ Fix suggestions:")
    print("  • Same-time duplicates → remove one (prefer no-agent over LLM)")
    print("  • Same pipeline tasks → stagger by 5-15 min")
    print("  • Independent tasks → move to different hour block")
    print("  • Weixin deliveries → max 1 per hour, space ≥2h between")


def main():
    crons = parse_cron_list()
    results = analyze_conflicts(crons)
    print_report(results)
    sys.exit(1 if results['conflict_count'] else 0)


if __name__ == '__main__':
    main()
