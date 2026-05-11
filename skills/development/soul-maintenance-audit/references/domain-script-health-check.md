# Domain Script Health Check Protocol

Systematic cross-domain Python script validation — verify all scripts in one or more Hermes domains are syntactically valid, have resolvable dependencies, and have safe import behavior.

## When to Run

- After bulk script changes or domain capability upgrades
- Periodic maintenance (monthly)
- User asks "检验/check X-domain 脚本"
- Before migrating or refactoring script directories

## 5-Stage Pipeline

### Stage 1: Inventory

```bash
# finance-domain scripts (live in ~/quant/)
ls ~/quant/*.py

# writing-domain core scripts (under a-share-* skills)
find ~/.hermes/profiles/writing-domain/skills/a-share-*/scripts/ -name "*.py"

# Other domains — check their SOUL.md "核心脚本" section
```

### Stage 2: Syntax Check (fast, no side-effects)

```python
import py_compile, glob

for f in glob.glob("~/quant/*.py"):
    try:
        py_compile.compile(f, doraise=True)
    except py_compile.PyCompileError as e:
        print(f"SYNTAX FAIL: {f} — {e}")
```

All scripts should pass. py_compile does NOT execute code, so no DB connections or side-effects.

### Stage 3: Import Availability (know your venv!)

Different domains use different virtual environments. Check SOUL.md or the script's shebang line to find the right Python.

```bash
# finance-domain uses ~/tools/quant_env/bin/python
~/tools/quant_env/bin/python -c "import tushare; import pyarrow; print('OK')"

# writing-domain uses system python3
python3 -c "import akshare; import playwright; import aiohttp; print('OK')"
```

**Pitfall**: akshare import can timeout (>10s) due to dynamic loading. This is a known issue — skip it in bulk import tests, verify separately.

### Stage 4: Pure-Library Import Test (no DB/network)

Separate scripts into two categories:

| Category | Examples | Test method |
|:---------|:---------|:------------|
| Pure library (no side-effects) | signal_engine, chan_buy_signal, policy_detect | Direct `importlib.import_module()` |
| DB/network-connecting | backfill_today_mysql, daily_kline_update, tushare_data_pipeline | Syntax-only, or test with DB down |

For pure library modules:
```python
import importlib
for mod in ['data_common', 'signal_engine', 'chan_buy_signal', ...]:
    importlib.import_module(mod)
```

### Stage 5: Side-Effect & Entry-Point Audit (CRITICAL)

This is the most important stage. Scripts without `if __name__ == "__main__"` guard execute top-level code on import — dangerous when other scripts import them.

**Detection script:**

```python
import ast

def check_script(path):
    with open(path) as f:
        tree = ast.parse(f.read())
    
    has_main = any(
        isinstance(node, ast.If) and 
        isinstance(node.test, ast.Compare) and
        isinstance(node.test.left, ast.Name) and
        node.test.left.id == '__name__'
        for node in ast.walk(tree)
    )
    
    top_level = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # docstring
        top_level.append(type(node).__name__)
    
    return has_main, top_level

# Scan all scripts
for script in all_scripts:
    has_main, top_level = check_script(script)
    if not has_main and top_level:
        print(f"RISK: {script} — no __main__ guard, top-level: {top_level[:5]}")
```

**Real-world incident (2026-05-07)**: `backfill_today_mysql.py` had no `__main__` guard and its top-level code executed `DELETE FROM kline WHERE trade_date='...'` on import. When the import test ran, it actually deleted today's MySQL data.

**Severity classification:**

| No guard + has top-level code | P0 | Import triggers DB writes/deletes/data mutations |
| No guard + only Assign/constants | P1 | Import is safe but blocks reuse as library |
| Has guard | OK | — |

### Fix Pattern

Wrap all top-level execution code:

```python
# BEFORE (runs on import — BAD)
engine = create_engine(DB_URL)
with engine.begin() as conn:
    conn.execute(text(f"DELETE FROM kline WHERE trade_date='{TODAY}'"))

# AFTER (only runs when executed as script)
def main():
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM kline WHERE trade_date='{TODAY}'"))

if __name__ == "__main__":
    main()
```

### Summary Report Template

```
=== DOMAIN SCRIPT HEALTH CHECK ===
Domain: finance-domain (~/quant/)
Scripts: 29
Syntax: 29/29 PASS
Import (pure lib): 10/10 PASS
Import (DB modules): X/Y PASS (Z skipped — DB down)
Entry-point guard: A/29 have __main__, B/29 RISK

Domain: writing-domain (a-share-*)
Scripts: 16
Syntax: 16/16 PASS
Deps: playwright OK, akshare OK, matplotlib OK, ...
Entry-point guard: X/16 have __main__, Y/16 RISK

CRITICAL: Z scripts with no __main__ guard + top-level code (P0)
```
