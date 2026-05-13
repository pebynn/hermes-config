#!/usr/bin/env python3
"""
audit_bd_layer.py — B/D层每日执行率审计 + GEPA 5道护栏 + Lessons遗忘机制

检查kanban.db中任务是否经过B/D层处理：
- B层指标：body含"已知陷阱"的task比例
- D层指标：result含[LESSONS]的task比例
- 低于阈值→QQ Bot告警

--extended 启用GEPA 5道护栏：
  1. 大小检查 - skill文件≤15KB, tool描述≤500字符
  2. pytest集成 - 有变更的skill/script自动跑关联测试
  3. 缓存兼容检查 - 扫描是否有中间会话变更
  4. 语义漂移检测 - LLM对比skill原始目的vs当前版本 (需--semantic)
  5. 审查门禁 - 对应L2/L3决策矩阵的变更审查提醒

lessons/遗忘机制：
  - 每条lesson加时间戳
  - 超过90天未确认→降权 (weight*0.5)
  - 超过180天→归档 (移至archive/)

用法: python3 audit_bd_layer.py [--extended] [--semantic] [--alert] [--json]
"""

import sys
import os
import sqlite3
import json
import uuid
import time
import subprocess
import tempfile
import shutil
from pathlib import Path
from fnmatch import fnmatch
from datetime import datetime, timedelta

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

KANBAN_DB = Path(os.path.expanduser("~/.hermes/kanban.db"))
THRESHOLD_B = 0.50
THRESHOLD_D = 0.20
LOOKBACK_HOURS = 24

SKILL_SIZE_LIMIT_KB = 15
SKILL_SIZE_LIMIT_BYTES = SKILL_SIZE_LIMIT_KB * 1024
TOOL_DESC_LIMIT_CHARS = 500

LESSONS_FILE = Path(os.path.expanduser("~/.hermes/lessons/lessons.jsonl"))
LESSONS_ARCHIVE_DIR = Path(os.path.expanduser("~/.hermes/lessons/archive"))
PROFILES_BASE = Path(os.path.expanduser("~/.hermes/profiles"))
SCRIPTS_DIR = Path(os.path.expanduser("~/.hermes/scripts"))
MEMORY_DIR = Path(os.path.expanduser("~/.hermes/memory"))
SESSIONS_DIR = Path(os.path.expanduser("~/.hermes/sessions"))

DECAY_DAYS = 90
ARCHIVE_DAYS = 180

# L2/L3 decision matrix — which file patterns require review
L2_PATTERNS = ["*/tools/*", "*/tool_*.py", "*/SKILL.md"]
L3_PATTERNS = ["*/SOUL.md", "*/system/*", "*/profiles/*/core/*", "*/code/*"]


# ══════════════════════════════════════════════════
# EXISTING: kanban.db B/D audit
# ══════════════════════════════════════════════════

def scan_kanban_db(db_path=None):
    """Scan kanban.db for B/D injection rates."""
    db = Path(db_path) if db_path else KANBAN_DB
    if not db.exists():
        return {"error": f"kanban.db not found at {db}"}

    conn = sqlite3.connect(str(db))
    since = int((datetime.now() - timedelta(hours=LOOKBACK_HOURS)).timestamp())

    cur = conn.execute(
        "SELECT count(*) FROM tasks WHERE created_at >= ?", (since,))
    total = cur.fetchone()[0]

    if total == 0:
        conn.close()
        return {"total": 0, "status": "no_tasks", "summary": "过去24h无新任务"}

    cur = conn.execute(
        "SELECT count(*) FROM tasks WHERE created_at >= ? AND body LIKE '%已知陷阱%'",
        (since,))
    b_count = cur.fetchone()[0]

    cur = conn.execute(
        "SELECT count(DISTINCT r.task_id) FROM task_runs r "
        "JOIN tasks t ON t.id=r.task_id "
        "WHERE t.created_at >= ? AND r.summary LIKE '%[LESSONS]%'",
        (since,))
    d_count = cur.fetchone()[0]

    cur = conn.execute(
        "SELECT count(DISTINCT r.task_id) FROM task_runs r "
        "JOIN tasks t ON t.id=r.task_id "
        "WHERE t.created_at >= ? AND r.outcome='completed'",
        (since,))
    done_with_runs = cur.fetchone()[0]

    conn.close()

    b_rate = b_count / total if total > 0 else 0
    d_rate = d_count / done_with_runs if done_with_runs > 0 else 0

    alerts = []
    if b_rate < THRESHOLD_B and total >= 3:
        alerts.append(f"B层注入率 {b_rate:.0%} < {THRESHOLD_B:.0%} ({b_count}/{total})")
    if d_rate < THRESHOLD_D and done_with_runs >= 2:
        alerts.append(f"D层回收率 {d_rate:.0%} < {THRESHOLD_D:.0%} ({d_count}/{done_with_runs})")

    return {
        "total": total,
        "done": done_with_runs,
        "b_count": b_count,
        "d_count": d_count,
        "b_rate": b_rate,
        "d_rate": d_rate,
        "alerts": alerts,
        "status": "critical" if alerts else "ok",
        "summary": f"B:{b_rate:.0%} D:{d_rate:.0%}" + (" ⚠️" if alerts else " ✅")
    }


# ══════════════════════════════════════════════════
# GUARDRAIL 1: Size Check
# ══════════════════════════════════════════════════

def _extract_yaml_frontmatter(content):
    """Extract YAML frontmatter from markdown. Returns dict or {}."""
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}
    # Simple key: value extraction (no full YAML parser to keep deps minimal)
    fm = {}
    for line in lines[1:end_idx]:
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def _scan_tool_descriptions(content):
    """Extract tool descriptions from markdown content. Returns list of (tool_name, desc)."""
    tools = []
    lines = content.split("\n")
    in_tools_section = False
    current_tool = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("tools:") or stripped.startswith("available_tools:"):
            in_tools_section = True
            continue
        if in_tools_section and stripped and not stripped.startswith(" ") and not stripped.startswith("-"):
            in_tools_section = False
            continue
        if in_tools_section:
            if stripped.startswith("- name:") or stripped.startswith("name:"):
                current_tool = stripped.split(":", 1)[1].strip()
            elif "description:" in stripped and current_tool:
                desc = stripped.split("description:", 1)[1].strip()
                tools.append((current_tool, desc))
                current_tool = None
    return tools


def check_size_limits(skills_base=None):
    """
    Guardrail 1: Check skill file size ≤15KB and tool descriptions ≤500 chars.
    Returns {"violations": [...], "checked": N, "status": "ok|warning"}
    """
    base = Path(skills_base) if skills_base else PROFILES_BASE
    violations = []
    checked = 0

    if not base.exists():
        return {"violations": [], "checked": 0, "status": "skipped",
                "summary": f"Skills base dir not found: {base}"}

    for skill_file in base.rglob("SKILL.md"):
        checked += 1
        try:
            size = skill_file.stat().st_size
            if size > SKILL_SIZE_LIMIT_BYTES:
                violations.append({
                    "file": str(skill_file),
                    "type": "size_exceeded",
                    "current_kb": round(size / 1024, 1),
                    "limit_kb": SKILL_SIZE_LIMIT_KB,
                    "message": f"Skill文件 {size/1024:.1f}KB > {SKILL_SIZE_LIMIT_KB}KB"
                })

            content = skill_file.read_text(encoding="utf-8", errors="replace")
            tools = _scan_tool_descriptions(content)
            for tool_name, desc in tools:
                if len(desc) > TOOL_DESC_LIMIT_CHARS:
                    violations.append({
                        "file": str(skill_file),
                        "type": f"tool_desc_exceeded:{tool_name}",
                        "current_chars": len(desc),
                        "limit_chars": TOOL_DESC_LIMIT_CHARS,
                        "message": f"Tool描述 '{tool_name}' {len(desc)}字符 > {TOOL_DESC_LIMIT_CHARS}"
                    })
        except Exception as e:
            violations.append({
                "file": str(skill_file),
                "type": "read_error",
                "message": str(e)
            })

    return {
        "violations": violations,
        "checked": checked,
        "status": "warning" if violations else "ok",
        "summary": f"检查{checked}个skill: {'⚠️' if violations else '✅'} {len(violations)}违规"
    }


# ══════════════════════════════════════════════════
# GUARDRAIL 2: pytest Integration
# ══════════════════════════════════════════════════

def check_pytest_integration(skills_dir=None, scripts_dir=None, lookback_hours=24):
    """
    Guardrail 2: Detect changed skills/scripts and run associated tests.
    Returns {"changed_files": [...], "test_results": {...}, "status": "ok|warning|error"}
    """
    skills = Path(skills_dir) if skills_dir else PROFILES_BASE
    scripts = Path(scripts_dir) if scripts_dir else SCRIPTS_DIR
    cutoff = time.time() - (lookback_hours * 3600)

    changed_files = []
    for scan_dir in [skills, scripts]:
        if not scan_dir.exists():
            continue
        for f in scan_dir.rglob("*.py"):
            try:
                if f.stat().st_mtime > cutoff:
                    changed_files.append(str(f))
            except OSError:
                pass
        for f in scan_dir.rglob("SKILL.md"):
            try:
                if f.stat().st_mtime > cutoff:
                    changed_files.append(str(f))
            except OSError:
                pass
        for f in scan_dir.rglob("*.sh"):
            try:
                if f.stat().st_mtime > cutoff:
                    changed_files.append(str(f))
            except OSError:
                pass

    if not changed_files:
        return {
            "changed_files": [],
            "test_results": {},
            "status": "ok",
            "summary": "无最近变更的文件，跳过pytest"
        }

    # Map changed files to test files
    test_paths = set()
    for cf in changed_files:
        p = Path(cf)
        # skill test: profiles/<name>/skills/<skill>/tests/
        if "skills" in str(p) and p.name == "SKILL.md":
            test_dir = p.parent / "tests"
            if test_dir.exists():
                test_paths.add(str(test_dir))
        # script test: scripts/tests/test_<name>.py
        if scripts and str(scripts) in str(p):
            test_file = scripts / "tests" / f"test_{p.stem}.py"
            if test_file.exists():
                test_paths.add(str(test_file))

    test_results = {}
    all_pass = True
    for tp in sorted(test_paths):
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", tp, "-q", "--tb=short"],
                capture_output=True, text=True, timeout=120,
                cwd=str(scripts)
            )
            test_results[tp] = {
                "exit_code": result.returncode,
                "output": result.stdout[-500:] if result.stdout else "",
                "passed": result.returncode == 0
            }
            if result.returncode != 0:
                all_pass = False
        except subprocess.TimeoutExpired:
            test_results[tp] = {"exit_code": -1, "output": "TIMEOUT", "passed": False}
            all_pass = False
        except Exception as e:
            test_results[tp] = {"exit_code": -1, "output": str(e), "passed": False}
            all_pass = False

    return {
        "changed_files": changed_files,
        "test_results": test_results,
        "status": "ok" if all_pass else "warning",
        "summary": f"变更{len(changed_files)}文件, 跑{len(test_paths)}测试: {'✅' if all_pass else '⚠️'}"
    }


# ══════════════════════════════════════════════════
# GUARDRAIL 3: Cache Compatibility
# ══════════════════════════════════════════════════

def check_cache_compat(lessons_dir=None, memory_dir=None, sessions_dir=None, lookback_hours=24):
    """
    Guardrail 3: Check if recent lesson/memory changes could invalidate cached sessions.
    Returns {"issues": [...], "status": "ok|warning"}
    """
    lessons = Path(lessons_dir) if lessons_dir else LESSONS_FILE.parent
    memory = Path(memory_dir) if memory_dir else MEMORY_DIR
    sessions = Path(sessions_dir) if sessions_dir else SESSIONS_DIR
    cutoff = time.time() - (lookback_hours * 3600)

    issues = []
    changed_items = []

    for scan_dir, label in [(lessons, "lessons"), (memory, "memory")]:
        if not scan_dir.exists():
            continue
        for f in scan_dir.rglob("*"):
            if f.is_file() and f.suffix not in (".pyc", ".pyo", ".lock"):
                try:
                    if f.stat().st_mtime > cutoff:
                        changed_items.append({"file": str(f), "type": label})
                except OSError:
                    pass

    if changed_items:
        # Check if there are active sessions that might use stale cache
        active_sessions = []
        if sessions.exists():
            for d in sessions.iterdir():
                if d.is_dir():
                    try:
                        mtime = d.stat().st_mtime
                        age_hours = (time.time() - mtime) / 3600
                        if age_hours < 48:  # sessions active in last 48h
                            active_sessions.append(str(d))
                    except OSError:
                        pass

        if active_sessions:
            issues.append({
                "type": "cache_invalidation_risk",
                "changed_items": len(changed_items),
                "active_sessions": len(active_sessions),
                "message": f"{len(changed_items)}个文件变更可能影响{len(active_sessions)}个活跃会话的缓存"
            })

    return {
        "issues": issues,
        "changed_count": len(changed_items),
        "status": "warning" if issues else "ok",
        "summary": f"缓存兼容: {'⚠️' if issues else '✅'} {len(changed_items)}变更/{len(issues)}问题"
    }


# ══════════════════════════════════════════════════
# GUARDRAIL 4: Semantic Drift Detection
# ══════════════════════════════════════════════════

def check_semantic_drift(skills_base=None, enable_llm=False):
    """
    Guardrail 4: Compare skill original purpose vs current version via LLM.
    Requires --semantic flag. Without it, returns skipped.
    Returns {"status": "skipped|ok|warning", "drifts": [...]}
    """
    if not enable_llm:
        return {
            "status": "skipped",
            "summary": "语义漂移检测需要 --semantic 标志 (LLM调用)",
            "drifts": []
        }

    base = Path(skills_base) if skills_base else PROFILES_BASE
    if not base.exists():
        return {"status": "skipped", "summary": "Skills dir not found", "drifts": []}

    drifts = []
    # Extract original purpose from skill name/description vs current content
    for skill_file in base.rglob("SKILL.md"):
        try:
            content = skill_file.read_text(encoding="utf-8", errors="replace")[:3000]
            fm = _extract_yaml_frontmatter(content)
            original_name = fm.get("name", skill_file.parent.name)
            original_desc = fm.get("description", "No description")

            # Simple heuristic: compare name vs content relevance
            # In production with LLM, this would call an API
            body = content.split("---\n", 2)[-1] if content.count("---") >= 2 else content
            name_in_body = original_name.lower() in body.lower()
            desc_in_body = any(
                word in body.lower()
                for word in original_desc.lower().split()[:5]
                if len(word) > 2
            )

            if not name_in_body or not desc_in_body:
                drifts.append({
                    "skill": str(skill_file),
                    "name": original_name,
                    "description_short": original_desc[:80],
                    "name_in_body": name_in_body,
                    "desc_in_body": desc_in_body,
                    "message": "技能名称/描述与正文内容可能偏离"
                })
        except Exception:
            continue

    return {
        "status": "warning" if drifts else "ok",
        "summary": f"语义漂移: {'⚠️' if drifts else '✅'} {len(drifts)}可疑 (启发式,非LLM)",
        "drifts": drifts
    }


# ══════════════════════════════════════════════════
# GUARDRAIL 5: Review Gate (L2/L3 Decision Matrix)
# ══════════════════════════════════════════════════

def _matches_any_pattern(filepath, patterns):
    """Check if filepath matches any glob pattern."""
    filepath = str(filepath)
    for pattern in patterns:
        if fnmatch(filepath, pattern):
            return True
    return False


def check_review_gate(skills_base=None, lookback_hours=24):
    """
    Guardrail 5: Check recent changes against L2/L3 decision matrix.
    L2 (tool desc, minor skill updates) → automated review
    L3 (system prompt, code evolution) → human review required
    Returns {"review_items": [...], "status": "ok|warning|critical"}
    """
    base = Path(skills_base) if skills_base else PROFILES_BASE
    cutoff = time.time() - (lookback_hours * 3600)

    review_items = []
    if not base.exists():
        return {"review_items": [], "status": "ok",
                "summary": "Skills base not found, 跳过审查门禁"}

    for changed_file in base.rglob("*"):
        if changed_file.is_dir():
            continue
        try:
            if changed_file.stat().st_mtime < cutoff:
                continue
        except OSError:
            continue

        # Only check relevant files
        if changed_file.suffix not in (".md", ".py", ".yaml", ".yml", ".json"):
            continue

        filepath = str(changed_file)

        if _matches_any_pattern(filepath, L3_PATTERNS):
            review_items.append({
                "file": filepath,
                "level": "L3",
                "action": "human_review_required",
                "message": "系统级变更需人工审核"
            })
        elif _matches_any_pattern(filepath, L2_PATTERNS):
            review_items.append({
                "file": filepath,
                "level": "L2",
                "action": "automated_review",
                "message": "工具/Skill变更需自动化审查"
            })

    critical_count = sum(1 for r in review_items if r["level"] == "L3")
    l2_count = sum(1 for r in review_items if r["level"] == "L2")

    status = "critical" if critical_count > 0 else ("warning" if l2_count > 0 else "ok")

    return {
        "review_items": review_items,
        "status": status,
        "summary": f"审查门禁: L3={critical_count}需人工 L2={l2_count}自动"
    }


# ══════════════════════════════════════════════════
# LESSONS FORGETTING MECHANISM
# ══════════════════════════════════════════════════

def add_lesson(lessons_path, lesson):
    """
    Add a lesson entry with auto-generated id and timestamp.
    lesson dict: {content, level, domain, [confirmed_at]}
    Returns the complete entry dict.
    """
    entry = {
        "id": str(uuid.uuid4())[:8],
        "content": lesson.get("content", ""),
        "level": lesson.get("level", "info"),
        "domain": lesson.get("domain", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "confirmed_at": lesson.get("confirmed_at"),
        "weight": 1.0,
        "status": "active"
    }

    path = Path(lessons_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def manage_lesson_decay(lessons_path=None):
    """
    Decay/archive lessons based on age.
    - >90 days unconfirmed → weight *= 0.5, status = "decayed"
    - >180 days unconfirmed → status = "archived", move to archive/
    Returns {"decayed": [...], "archived": [...], "kept": N}
    """
    path = Path(lessons_path) if lessons_path else LESSONS_FILE
    if not path.exists():
        return {"decayed": [], "archived": [], "kept": 0, "summary": "无lessons文件"}

    now = datetime.now()
    decayed = []
    archived = []
    kept = []

    try:
        with open(path, "r") as f:
            lines = f.readlines()
    except Exception as e:
        return {"decayed": [], "archived": [], "kept": 0, "summary": f"读取失败: {e}"}

    new_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            new_lines.append(line + "\n")
            continue

        # Determine age based on last confirmation or timestamp
        confirmed = entry.get("confirmed_at")
        created = entry.get("timestamp", "")
        ref_date_str = confirmed if confirmed else created
        if not ref_date_str:
            kept.append(entry)
            new_lines.append(json.dumps(entry, ensure_ascii=False) + "\n")
            continue

        try:
            ref_date = datetime.fromisoformat(ref_date_str)
        except (ValueError, TypeError):
            kept.append(entry)
            new_lines.append(json.dumps(entry, ensure_ascii=False) + "\n")
            continue

        age_days = (now - ref_date).days

        if age_days > ARCHIVE_DAYS:
            entry["status"] = "archived"
            archived.append(entry)
            archive_path = LESSONS_ARCHIVE_DIR / f"archived_{entry['id']}.json"
            LESSONS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            with open(archive_path, "w") as af:
                json.dump(entry, af, ensure_ascii=False, indent=2)
        elif age_days > DECAY_DAYS and entry.get("status") != "decayed":
            entry["weight"] = entry.get("weight", 1.0) * 0.5
            entry["status"] = "decayed"
            entry["decayed_at"] = now.isoformat()
            decayed.append(entry)
            new_lines.append(json.dumps(entry, ensure_ascii=False) + "\n")
        else:
            kept.append(entry)
            new_lines.append(json.dumps(entry, ensure_ascii=False) + "\n")

    # Write back (without archived entries)
    with open(path, "w") as f:
        f.writelines(new_lines)

    return {
        "decayed": decayed,
        "archived": archived,
        "kept": len(kept),
        "summary": f"降权{len(decayed)} 归档{len(archived)} 保留{len(kept)}"
    }


# ══════════════════════════════════════════════════
# EXTENDED AUDIT ORCHESTRATOR
# ══════════════════════════════════════════════════

def run_extended_audit(db_path=None, skills_base=None, lessons_file=None,
                       enable_semantic=False, lookback_hours=24):
    """
    Run all 5 guardrails + lessons decay + kanban B/D audit.
    Returns dict with results from all checks.
    """
    return {
        "bd_injection": scan_kanban_db(db_path),
        "size_check": check_size_limits(skills_base),
        "pytest_check": check_pytest_integration(
            skills_dir=skills_base or str(PROFILES_BASE),
            scripts_dir=str(SCRIPTS_DIR),
            lookback_hours=lookback_hours
        ),
        "cache_check": check_cache_compat(
            lessons_dir=str(LESSONS_FILE.parent) if lessons_file is None
            else str(Path(lessons_file).parent),
            memory_dir=str(MEMORY_DIR),
            sessions_dir=str(SESSIONS_DIR),
            lookback_hours=lookback_hours
        ),
        "review_gate": check_review_gate(skills_base, lookback_hours),
        "semantic_drift": check_semantic_drift(skills_base, enable_llm=enable_semantic),
        "lesson_decay": manage_lesson_decay(lessons_file or str(LESSONS_FILE)),
    }


# ══════════════════════════════════════════════════
# MAIN / CLI
# ══════════════════════════════════════════════════

def main():
    extended = "--extended" in sys.argv
    semantic = "--semantic" in sys.argv
    use_json = "--json" in sys.argv
    use_alert = "--alert" in sys.argv

    if extended:
        result = run_extended_audit(enable_semantic=semantic)
    else:
        result = scan_kanban_db()

    if use_json:
        print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
        return

    if use_alert and not extended:
        if isinstance(result, dict) and result.get("alerts"):
            for a in result["alerts"]:
                print(f"⚠️ {a}")
        return

    # Pretty print
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"B/D层审计 ({now_str})")
    print("=" * 50)

    if extended:
        sections = [
            ("B/D注入率", result.get("bd_injection", {})),
            ("大小检查", result.get("size_check", {})),
            ("Pytest集成", result.get("pytest_check", {})),
            ("缓存兼容", result.get("cache_check", {})),
            ("审查门禁", result.get("review_gate", {})),
            ("语义漂移", result.get("semantic_drift", {})),
            ("Lessons遗忘", result.get("lesson_decay", {})),
        ]
        for title, data in sections:
            summary = data.get("summary", str(data)) if isinstance(data, dict) else str(data)
            icon = "✅" if isinstance(data, dict) and data.get("status") == "ok" else "📋"
            print(f"  {icon} {title}: {summary}")

        all_ok = all(
            isinstance(r, dict) and r.get("status") == "ok"
            for r in [
                result.get("bd_injection", {}),
                result.get("size_check", {}),
                result.get("pytest_check", {}),
                result.get("cache_check", {}),
                result.get("review_gate", {}),
            ]
        )
        print(f"\n{'✅ 全部通过' if all_ok else '⚠️ 有问题需关注'}")
    else:
        bd = result
        print(f"  过去24h任务: {bd.get('total', 0)}")
        print(f"  B层注入: {bd.get('b_rate', 0):.0%} ({bd.get('b_count', 0)}/{bd.get('total', 0)})")
        print(f"  D层回收: {bd.get('d_rate', 0):.0%} ({bd.get('d_count', 0)}/{bd.get('done', 0)})")
        if bd.get("alerts"):
            print(f"\n⚠️ 告警:")
            for a in bd["alerts"]:
                print(f"  - {a}")
        else:
            print(f"\n✅ 正常")


if __name__ == "__main__":
    main()
