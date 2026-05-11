# grep for Code Analysis — Pitfalls & Patterns

## rg vs grep in Python subprocess

**Pitfall:** `rg` (ripgrep) may return exit code 2 when passed multiple directories as
Python subprocess args, even though it works fine from the shell directly.

```python
# DON'T: rg can fail in subprocess with exit code 2 on multi-dir search
import subprocess
result = subprocess.run(
    ["rg", "-n", r"\bcheck_foo\s*\(", "/dir1", "/dir2", "/dir3"],
    capture_output=True, text=True, timeout=30
)
# result.stdout may be empty, result.returncode may be 2
```

```python
# DO: use grep instead when reliability matters
result = subprocess.run(
    ["grep", "-rn", r"\bcheck_foo\s*\(", "/dir1", "/dir2", "/dir3"],
    capture_output=True, text=True, timeout=30
)
```

**Why:** `rg` checks each path argument against file- and directory-level glob
filters (like `.gitignore`, `.rgignore`, and its own `--include`/`--type`
flags). When a directory has no files matching the implicit or explicit
filter, rg exits 2 ("no results"). In contrast, `grep` returns 1 for "no
matches" and only returns 2 for actual errors.

**Workaround if you need rg features** (speed, PCRE2, type filters):
- Pass `--no-ignore --no-ignore-global` to skip gitignore filtering
- Check `returncode` explicitly: treat 0=found, 1=no-match, 2=error
- Always check stderr for real errors when returncode is non-zero

## Efficiency patterns for .py file scanning

**Scenario A — Check if a function is called anywhere (dead code detection)**

```python
import subprocess

def find_call_sites(funcname, directories):
    """Find all call sites of a function across directories.
    Returns dict of {filepath: [line_numbers]}."""
    result = subprocess.run(
        ["grep", "-rn", f"\\b{funcname}\\s*("] + directories,
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 1 or not result.stdout.strip():
        return {}  # not called anywhere
    sites = {}
    for line in result.stdout.strip().split('\n'):
        parts = line.split(':', 2)
        if len(parts) >= 2:
            fpath, lineno = parts[0], parts[1]
            sites.setdefault(fpath, []).append(int(lineno))
    return sites
```

**Scenario B — Filter out definition lines from call-site results**

A grep for `\bcheck_foo\(` also matches the `def check_foo(` line. To
distinguish definitions from calls:

```python
from pathlib import Path
import re

DEF_PATTERN = re.compile(r'^\s*(?:async\s+)?def\s+\w+\s*\(')

def is_def_line(line_content):
    """Check if the matched line is a function definition, not a call."""
    return bool(DEF_PATTERN.search(line_content))
```

**Scenario C — Pre-filter with rg for speed, verify with grep for accuracy**

For very large codebases (thousands of files), rg is 5-10x faster:

```python
# Fast pass with rg (may miss some due to ignore files)
fast = subprocess.run(
    ["rg", "-n", "--no-ignore", f"\\b{name}\\s*(", "/dir"],
    capture_output=True, text=True, timeout=10
)
# If rg found nothing, re-verify with grep (slower but reliable)
if fast.returncode != 0:
    verify = subprocess.run(
        ["grep", "-rn", f"\\b{name}\\s*(", "/dir"],
        capture_output=True, text=True, timeout=60
    )
```

## Common pitfalls with grep-based code search

1. **Word boundary (`\b`) only works for C-identifier characters.**
   Functions named with underscores are fine. For names with dots (e.g.,
   `module.func`), use `\.func` instead.

2. **Over-matching on short names.**
   A function named `run` matches `subprocess.run(...)`, `run_script(...)`,
   `rerun(...)`. Use `\brun\(` to require paren immediately (vs `\brun\s*\(`
   which allows spaces).

3. **Missed calls with indirection.**
   `getattr(obj, "func_name")()`, `methods["func"]`, and `locals()["func"]`
   won't be found. These need AST parsing for accurate detection.

4. **Escape sequences.** In f-strings inside Python subprocess args, you need
   double-escaped backslashes: `f"\\b{name}\\s*\\("` → `\bfunc\s*\(`.

5. **Timeout on large directory trees.** If a directory has millions of lines,
   set a timeout and fall back to file-by-file scanning with batching.

## Example: full dead-code analysis skeleton

See `/home/pebynn/.hermes/tmp/dead_code_analysis.py` for a complete working
example that scans 100+ files across 3 directories for dead function/class
definitions.
