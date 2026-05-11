#!/usr/bin/env python3
"""pipeline_fix_except_pass.py — collect_data.py except pass 加固"""
from pathlib import Path
import py_compile

path = Path('/home/pebynn/writing-data/scripts/collect_data.py')
content = path.read_text()

old = 'except Exception: pass'
new = 'except Exception as e: print(f"[warn] 交易日校验失败: {e}")'

if old in content:
    content = content.replace(old, new, 1)
    path.write_text(content)
    py_compile.compile(str(path), doraise=True)
    print(f"✅ except pass 已替换 → print警告")
else:
    print(f"⏭️ 未找到 'except Exception: pass' (可能已修复)")
