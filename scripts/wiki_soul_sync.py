#!/usr/bin/env python3
"""Wiki soul 自动同步 — SOUL.md 改动后同步到 ~/brain/soul/"""
import shutil
from pathlib import Path

HOME = Path.home()
SOURCE = HOME / '.hermes' / 'SOUL.md'
PROFILES = HOME / '.hermes' / 'profiles'
TARGET = HOME / 'brain' / 'soul'

TARGET.mkdir(parents=True, exist_ok=True)

# 同步主 SOUL
main_target = TARGET / 'hermes-main.md'
if SOURCE.exists():
    shutil.copy2(SOURCE, main_target)
    print(f"✅ hermes-main.md ({SOURCE.stat().st_size} bytes)")

# 同步域 SOUL
for profile_dir in PROFILES.iterdir():
    if not profile_dir.is_dir():
        continue
    soul = profile_dir / 'SOUL.md'
    if soul.exists():
        domain = profile_dir.name  # code-domain, ec-domain, etc.
        target = TARGET / f'{domain}.md'
        shutil.copy2(soul, target)
        print(f"✅ {domain}.md ({soul.stat().st_size} bytes)")

print(f"\n已同步到 {TARGET} ({sum(1 for _ in TARGET.glob('*.md'))} 文件)")
