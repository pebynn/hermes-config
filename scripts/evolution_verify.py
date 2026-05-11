#!/usr/bin/env python3
"""
evolution_verify.py — P+B+C+D+N 自主进化闭环验证脚本

验证内容：
1. B层：lessons 文件是否有 CRITICAL 条目（有内容=可注入）
2. C层：lessons 文件最后修改时间（>3天无修改=学习停滞）
3. D层：graphify 同步是否正常（检查 cron e07573d46f12 运行状态）
4. 完整性：各域 CRITICAL 条目数量统计

Usage:
  python3 evolution_verify.py              # 完整验证
  python3 evolution_verify.py --brief      # 仅输出异常
"""

import os, sys, json, re
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
LESSONS_DIR = BASE / "lessons"
GRAPH_PATH = Path("/home/pebynn/brain/graphify-out/graph.json")
CRON_DB = BASE / "cron" / "jobs.json"
TZ = timezone(timedelta(hours=8))  # Asia/Shanghai

SKIP_FILES = re.compile(r"^_")

def parse_critical_count(filepath: Path) -> int:
    """统计文件的 CRITICAL 条目数"""
    if not filepath.exists():
        return 0
    text = filepath.read_text(encoding="utf-8", errors="replace")
    # 统计 ## 🔴 行数
    return len(re.findall(r"^## 🔴", text, re.MULTILINE))

def check_graph_sync() -> dict:
    """检查 graphify 同步状态"""
    result = {"graph_exists": GRAPH_PATH.exists(), "synced_lessons": 0, "stale_days": None}
    if not result["graph_exists"]:
        return result

    try:
        with open(GRAPH_PATH) as f:
            graph = json.load(f)
        # 统计 lesson 节点
        for node in graph.get("nodes", []):
            if node.get("file_type") == "lesson" or "lesson" in node.get("id", ""):
                result["synced_lessons"] += 1
        # 检查 graph 最后修改时间
        mtime = datetime.fromtimestamp(GRAPH_PATH.stat().st_mtime, tz=TZ)
        result["graph_mtime"] = mtime.strftime("%Y-%m-%d %H:%M")
        result["stale_days"] = (datetime.now(TZ) - mtime).days
    except Exception as e:
        result["error"] = str(e)
    return result

def check_cron_status() -> dict:
    """检查 lessons-to-graphify cron 运行状态"""
    result = {"job_id": "e07573d46f12", "exists": False, "last_run": None, "last_status": None}
    if not CRON_DB.exists():
        return result
    try:
        with open(CRON_DB) as f:
            jobs = json.load(f)
        for job in jobs if isinstance(jobs, list) else jobs.get("jobs", []):
            if job.get("id") == result["job_id"] or job.get("job_id") == result["job_id"]:
                result["exists"] = True
                result["last_run"] = job.get("last_run_at") or job.get("last_completed_at")
                result["last_status"] = job.get("last_status")
                break
    except Exception:
        pass
    return result

def main():
    brief = "--brief" in sys.argv

    if not brief:
        print("🔍 P+B+C+D+N 自主进化闭环验证")
        print(f"   时间: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M')}")
        print()

    issues = []
    stats = {}

    # 1. 扫描 lessons 文件
    for fpath in sorted(LESSONS_DIR.glob("*.md")):
        if SKIP_FILES.match(fpath.name):
            continue
        domain = fpath.stem
        critical = parse_critical_count(fpath)
        mtime = datetime.fromtimestamp(fpath.stat().st_mtime, tz=TZ)
        days_stale = (datetime.now(TZ) - mtime).days

        stats[domain] = {"critical": critical, "stale_days": days_stale, "mtime": mtime.strftime("%m-%d %H:%M")}

        if days_stale > 7:
            issues.append(f"⚠️ {domain}: {days_stale}天无新教训写入 (C层可能停滞)")
        elif days_stale > 3 and critical == 0:
            issues.append(f"⚡ {domain}: {days_stale}天无修改且0条CRITICAL")

    # 2. 检查 graphify 同步
    graph = check_graph_sync()
    cron_status = check_cron_status()

    if graph["stale_days"] and graph["stale_days"] > 2:
        issues.append(f"⚠️ graphify: {graph['stale_days']}天未更新 (D层同步可能断裂)")

    if not cron_status["exists"]:
        issues.append("🔴 cron e07573d46f12 未找到 (同步cron缺失)")
    elif cron_status["last_status"] and cron_status["last_status"] != "completed":
        issues.append(f"🔴 cron e07573d46f12 上次状态: {cron_status['last_status']}")

    # 3. 输出
    if not brief:
        print("📊 各域 CRITICAL 教训:")
        for domain, s in stats.items():
            bar = "🔴" * min(s["critical"], 5) if s["critical"] > 0 else "·"
            print(f"  {domain:20s} {bar} {s['critical']}条  最后修改: {s['mtime']} ({s['stale_days']}天前)")

        print(f"\n📊 Graphify 同步:")
        print(f"  已同步 lessons: {graph.get('synced_lessons', '?')} 节点")
        print(f"  最后更新: {graph.get('graph_mtime', '?')}")
        print(f"  Cron状态: {'✅' if cron_status.get('last_status') == 'completed' else '⚠️'}")

    if issues:
        print(f"\n⚠️ {len(issues)} 个异常:")
        for i in issues:
            print(f"  {i}")
        sys.exit(1)
    else:
        if not brief:
            print("\n✅ 自主进化闭环运行正常")
        sys.exit(0)

if __name__ == "__main__":
    main()
