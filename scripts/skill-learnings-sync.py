#!/usr/bin/env python3
"""扫描 agent 自建技能变更 → 写摘要到 brain，供 gbrain-sync 索引"""

import json, os, time
from pathlib import Path

SKILLS_DIR = Path.home() / ".hermes" / "skills"
BRAIN_LEARNINGS = Path.home() / "brain" / "agent" / "learnings"
STATE_FILE = Path.home() / ".hermes" / ".skill_learnings_state.json"
BUNDLED_MANIFEST = SKILLS_DIR / ".bundled_manifest"
HUB_LOCK = SKILLS_DIR / ".hub" / "lock.json"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_scan": 0, "known_skills": {}}


def save_state(state):
    BRAIN_LEARNINGS.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def load_bundled_and_hub():
    """加载 bundled + hub 技能名列表"""
    protected = set()
    for f in [BUNDLED_MANIFEST, HUB_LOCK]:
        if f.exists():
            try:
                data = json.loads(f.read_text())
                if isinstance(data, list):
                    protected.update(data)
                elif isinstance(data, dict):
                    protected.update(data.keys())
            except (json.JSONDecodeError, KeyError):
                pass
    return protected


def scan_agent_skills():
    protected = load_bundled_and_hub()
    state = load_state()
    now = time.time()
    new_findings = []

    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        if skill_dir.name in protected:
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        mtime = skill_md.stat().st_mtime
        known = state["known_skills"].get(skill_dir.name, {})
        last_mtime = known.get("mtime", 0)

        if mtime > max(last_mtime, state["last_scan"]):
            # 读取 SKILL.md 前几行获取描述
            content = skill_md.read_text()[:2000]
            desc = ""
            for line in content.split("\n"):
                if line.startswith("description:"):
                    desc = line.split("description:", 1)[1].strip()
                    break

            if not desc:
                # fallback: 取 frontmatter 后的第一段
                in_frontmatter = False
                frontmatter_done = False
                for line in content.split("\n"):
                    if line.strip() == "---":
                        if not in_frontmatter:
                            in_frontmatter = True
                        elif in_frontmatter:
                            frontmatter_done = True
                        continue
                    if frontmatter_done and line.strip() and not line.startswith("#"):
                        desc = line.strip()[:200]
                        break

            new_findings.append(
                {
                    "skill": skill_dir.name,
                    "desc": desc or "(无描述)",
                    "mtime": mtime,
                    "is_new": last_mtime == 0,
                }
            )

            state["known_skills"][skill_dir.name] = {"mtime": mtime}

    state["last_scan"] = now
    save_state(state)
    return new_findings


def write_to_brain(findings):
    if not findings:
        return

    date_str = time.strftime("%Y-%m-%d")
    out_path = BRAIN_LEARNINGS / f"skill-sync-{date_str}.md"
    existing = ""
    if out_path.exists():
        existing = out_path.read_text()

    new_lines = []
    for f in findings:
        tag = "新技能" if f["is_new"] else "更新"
        new_lines.append(f"- [{tag}] **{f['skill']}**: {f['desc']}")

    if existing:
        # 追加重不覆写
        out_path.write_text(existing.rstrip() + "\n" + "\n".join(new_lines) + "\n")
    else:
        out_path.write_text(
            f"# Agent 技能学习同步 — {date_str}\n\n" + "\n".join(new_lines) + "\n"
        )

    print(f"Wrote {len(findings)} findings → {out_path}")


if __name__ == "__main__":
    findings = scan_agent_skills()
    write_to_brain(findings)
    if not findings:
        print("No new agent skill learnings.")
