#!/usr/bin/env python3
"""检测并清理 profile 下与 master 重复的 skill 副本。

用法:
  python3 profile-skill-dedup.py           # 检测（dry-run）
  python3 profile-skill-dedup.py --delete   # 删除纯重复副本

输出:
  - 统计各 profile skill 数量 vs master
  - 列出过期副本（内容哈希与 master 不一致）
  - --delete 模式下删除与 master 完全一致的副本目录
"""

import os, hashlib, shutil, sys
from pathlib import Path

MASTER_DIR = Path.home() / '.hermes' / 'skills'
PROFILES_DIR = Path.home() / '.hermes' / 'profiles'


def build_master_index():
    index = {}
    for f in MASTER_DIR.rglob('SKILL.md'):
        rel = str(f.relative_to(MASTER_DIR))
        index[rel] = hashlib.md5(f.read_bytes()).hexdigest()
    return index


def scan_profiles(master_index):
    results = []
    for pf in sorted(PROFILES_DIR.iterdir()):
        if not pf.is_dir():
            continue
        skills_dir = pf / 'skills'
        if not skills_dir.exists():
            continue
        
        identical = []
        stale = []
        unique = []
        
        for f in sorted(skills_dir.rglob('SKILL.md')):
            rel = str(f.relative_to(skills_dir))
            fhash = hashlib.md5(f.read_bytes()).hexdigest()
            
            if rel in master_index:
                if fhash == master_index[rel]:
                    identical.append((f, rel))
                else:
                    stale.append((f, rel, fhash))
            else:
                unique.append((f, rel))
        
        results.append({
            'domain': pf.name,
            'identical': identical,
            'stale': stale,
            'unique': unique,
        })
    
    return results


def print_report(results):
    total_identical = sum(len(r['identical']) for r in results)
    total_stale = sum(len(r['stale']) for r in results)
    total_unique = sum(len(r['unique']) for r in results)
    
    print(f"Master skills: {len(build_master_index())}")
    print(f"Profile skill instances: {total_identical + total_stale + total_unique}")
    print(f"  Identical to master: {total_identical}")
    print(f"  Stale (differs):     {total_stale}")
    print(f"  Domain-specific:     {total_unique}")
    print()
    
    for r in results:
        print(f"{r['domain']}: {len(r['identical'])} identical, {len(r['stale'])} stale, {len(r['unique'])} unique")
    
    if total_stale > 0:
        print(f"\nStale copies (review before deleting):")
        for r in results:
            for f, rel, _ in r['stale']:
                print(f"  {r['domain']}/{rel}")
    
    return total_identical


def delete_identical(results):
    deleted = 0
    for r in results:
        for f, rel in r['identical']:
            skill_root = f.parent
            if skill_root != (PROFILES_DIR / r['domain'] / 'skills'):
                shutil.rmtree(skill_root)
                deleted += 1
    
    # Clean empty dirs
    for pf in PROFILES_DIR.iterdir():
        if not pf.is_dir():
            continue
        skills_dir = pf / 'skills'
        if not skills_dir.exists():
            continue
        for d in sorted(skills_dir.rglob('*'), reverse=True):
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
    
    return deleted


if __name__ == '__main__':
    master_index = build_master_index()
    results = scan_profiles(master_index)
    
    if '--delete' in sys.argv:
        deleted = delete_identical(results)
        print(f"\nDeleted {deleted} identical skill copies.")
    else:
        total = print_report(results)
        if total > 0:
            print(f"\nRun with --delete to remove {total} identical copies.")
