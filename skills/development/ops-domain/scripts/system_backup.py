#!/usr/bin/env python3
"""
system_backup.py — 系统配置备份脚本

备份 Hermes 配置文件到 ~/backups/{YYYY-MM-DD}/
保留最近 7 天备份，自动清理更旧的。
输出备份清单 JSON 到 stdout。
"""

import json
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────
HOME = Path.home()
HERMES_DIR = HOME / ".hermes"
BACKUP_ROOT = HOME / "backups"
RETENTION_DAYS = 7
DATE_STR = datetime.now().strftime("%Y-%m-%d")
BACKUP_DIR = BACKUP_ROOT / DATE_STR

# 要备份的文件/目录列表（相对于 HERMES_DIR 的路径）
BACKUP_PATTERNS = [
    "config.yaml",
    "SOUL.md",
    ".env",
    "auth.json",
    "profiles/*/SOUL.md",
    "profiles/*/config.yaml",
]


def collect_files() -> list[Path]:
    """收集所有需要备份的文件，返回绝对路径列表。"""
    files: list[Path] = []
    for pattern in BACKUP_PATTERNS:
        glob_path = HERMES_DIR / pattern
        matched = list(HERMES_DIR.glob(pattern))
        if not matched:
            # 尝试直接用 stat 检查固定文件
            if "*" not in pattern and glob_path.exists():
                files.append(glob_path.resolve())
            continue
        for p in matched:
            if p.is_file():
                files.append(p.resolve())
    return files


def backup_files(files: list[Path]) -> list[str]:
    """
    将文件复制到备份目录，保留元数据。
    返回相对路径清单（相对于备份目录）。
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    manifest: list[str] = []
    for src in files:
        try:
            # 计算相对路径，保持目录结构
            rel_path = src.relative_to(HERMES_DIR)
        except ValueError:
            # 如果文件在 HERMES_DIR 外，直接用文件名
            rel_path = src.name

        dst = BACKUP_DIR / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(str(src), str(dst))  # copy2 保留元数据
        manifest.append(str(rel_path))

    return sorted(manifest)


def clean_old_backups() -> int:
    """删除超过 RETENTION_DAYS 的旧备份目录，返回删除数量。"""
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    removed = 0

    if not BACKUP_ROOT.exists():
        return 0

    for entry in sorted(BACKUP_ROOT.iterdir()):
        if not entry.is_dir():
            continue
        try:
            dir_date = datetime.strptime(entry.name, "%Y-%m-%d")
        except ValueError:
            continue  # 不是日期格式的目录，跳过

        if dir_date < cutoff:
            shutil.rmtree(str(entry))
            removed += 1

    return removed


def compute_total_size(manifest: list[str]) -> int:
    """计算备份文件总大小（KB，向上取整）。"""
    total_bytes = 0
    for rel_path in manifest:
        f = BACKUP_DIR / rel_path
        if f.exists():
            total_bytes += f.stat().st_size
    # 返回 KB，至少 1
    return max(1, (total_bytes + 1023) // 1024)


def main():
    files = collect_files()
    manifest = backup_files(files)
    removed = clean_old_backups()
    total_kb = compute_total_size(manifest)

    output = {
        "日期": DATE_STR,
        "备份目录": f"~/{str(BACKUP_DIR.relative_to(HOME))}/",
        "文件数": len(manifest),
        "总大小KB": total_kb,
        "文件清单": manifest,
        "清理": {
            "删除旧备份数": removed,
            "保留天数": RETENTION_DAYS,
        },
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
