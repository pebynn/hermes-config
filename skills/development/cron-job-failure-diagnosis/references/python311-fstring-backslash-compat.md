# Python 3.11 F-String Backslash Compatibility

## The Problem

Python 3.11 does NOT support backslashes (`\n`, `\t`, etc.) inside f-string expression parts. Python 3.12+ does (PEP 701).

This causes a `SyntaxError` at runtime when a script compiled under Python 3.12 is run under Python 3.11.

## Symptom

```
File "agenda_builder.py", line 404
    print(f"✅ done ({len('\\n'.join(items))} chars)")
                                 ^^
SyntaxError: f-string expression part cannot include a backslash
```

The script passes `py_compile` on the host system (Python 3.12) but fails when the **runtime interpreter** is 3.11.

## Root Cause

Hermes cron scheduler uses `~/.hermes/hermes-agent/venv/bin/python3` which is **Python 3.11.15**. But `#!/usr/bin/env python3` (system Python) is **3.12.3**.

When cron runs `no_agent` scripts, it uses the venv's Python 3.11, not the system's Python 3.12.

## Fix

**Before** (breaks on 3.11):
```python
print(f"✅ done ({len('\\n'.join(items))} chars)")
```

**After** (works on both 3.11 and 3.12):
```python
content = '\n'.join(items)
print(f"✅ done ({len(content)} chars)")
```

Or equivalently for any f-string expression containing a backslash:

```python
# BAD: backslash in f-string expression
f"({len('\\n'.join(data))})"     # Python ≥3.12 only

# GOOD: pre-compute to variable
joined = '\\n'.join(data)
f"({len(joined)})"               # Python ≥3.10 compatible
```

## Detection

Run a quick scan for any f-string containing backslashes in cron scripts:

```bash
grep -rn 'f".*\\\.*{' ~/.hermes/scripts/ --include='*.py'
grep -rn "f'.*\\\.*{" ~/.hermes/scripts/ --include='*.py'
```

## Prevention

When writing cron scripts (which run under Python 3.11 venv):

1. **Never** put `\n`, `\t`, `\\`, or any backslash escape inside f-string `{}` expressions
2. Pre-compute the string with the escape to a variable first
3. Test under the venv Python: `~/.hermes/hermes-agent/venv/bin/python3 -c "import py_compile; py_compile.compile('script.py', doraise=True)"`
