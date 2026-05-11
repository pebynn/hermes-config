#!/usr/bin/env python3
"""Lock profile skills/ dirs to prevent hermes auto-rebundle.
Usage:
  python3 lock_profile_skills.py <profile_name>    # Lock single profile
  python3 lock_profile_skills.py --all              # Lock all profiles  
  python3 lock_profile_skills.py --verify           # Check all profiles
"""
import os, stat, shutil, sys, argparse

PROFILES_DIR = os.path.expanduser("~/.hermes/profiles")

def clean_and_lock(profile_path):
    """Remove all skills except devops/kanban-worker, chmod 555 everything."""
    skills_dir = os.path.join(profile_path, "skills")
    if not os.path.isdir(skills_dir):
        return False, "no skills dir"
    
    # 1. Remove all non-kanban-worker skill dirs
    devops_dir = os.path.join(skills_dir, "devops")
    for item in os.listdir(skills_dir):
        item_path = os.path.join(skills_dir, item)
        if item.startswith('.'):
            continue
        if os.path.isdir(item_path) and item == "devops":
            for sub in os.listdir(item_path):
                sub_path = os.path.join(item_path, sub)
                if sub != "kanban-worker" and os.path.isdir(sub_path):
                    os.chmod(sub_path, stat.S_IRWXU)
                    shutil.rmtree(sub_path)
        elif os.path.isdir(item_path):
            os.chmod(item_path, stat.S_IRWXU)
            shutil.rmtree(item_path)
    
    # 2. Remove bundled_manifest and snapshot
    for f in [".bundled_manifest"]:
        p = os.path.join(skills_dir, f)
        if os.path.exists(p): os.remove(p)
    for f in [".skills_prompt_snapshot.json"]:
        p = os.path.join(profile_path, f)
        if os.path.exists(p): os.remove(p)
    
    # 3. Lock: skills/ (555)
    os.chmod(skills_dir, stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    # Lock: devops/ (555)
    if os.path.isdir(devops_dir):
        os.chmod(devops_dir, stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    # Lock: kanban-worker/ (555)
    kw_dir = os.path.join(devops_dir, "kanban-worker") if os.path.isdir(devops_dir) else None
    if kw_dir and os.path.isdir(kw_dir):
        os.chmod(kw_dir, stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    
    # Count remaining
    count = 0
    for root, dirs, files in os.walk(skills_dir):
        if "SKILL.md" in files and root != skills_dir:
            count += 1
    return True, f"{count} skills locked"

def verify(profile_path):
    """Check profile skill count and perms."""
    skills_dir = os.path.join(profile_path, "skills")
    if not os.path.isdir(skills_dir):
        return False, "no skills dir"
    count = 0
    for root, dirs, files in os.walk(skills_dir):
        if "SKILL.md" in files and root != skills_dir:
            count += 1
    mode = oct(os.stat(skills_dir).st_mode)[-3:]
    return count == 1, f"{count} skills (perms={mode})"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", nargs="?", help="Profile name or --all/--verify")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    profiles = []
    if args.verify or args.all:
        profiles = [d for d in os.listdir(PROFILES_DIR) 
                   if os.path.isdir(os.path.join(PROFILES_DIR, d)) and not d.startswith('.')]
    elif args.profile:
        profiles = [args.profile]
    else:
        parser.print_help()
        sys.exit(1)

    for name in profiles:
        path = os.path.join(PROFILES_DIR, name)
        if args.verify:
            ok, msg = verify(path)
            print(f"  {'✓' if ok else '⚠'} {name}: {msg}")
        else:
            ok, msg = clean_and_lock(path)
            print(f"  {'✓' if ok else '✗'} {name}: {msg}")

if __name__ == "__main__":
    main()
