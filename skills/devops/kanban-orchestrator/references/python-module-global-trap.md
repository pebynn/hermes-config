# Python Module-Level `global` Trap in if __name__ == "__main__"

## Symptom

```python
START_DATE = "2021-01-01"

if __name__ == "__main__":
    global START_DATE   # SyntaxError!
    START_DATE = args.start
```

Produces: `SyntaxError: name 'START_DATE' is assigned to before global declaration`

## Root cause

Python's `if __name__ == "__main__":` block is NOT a function scope — it's still module-level code. But Python treats any assignment to `START_DATE` within the block as a local binding conflict because the name was already defined at module level. The `global` keyword doesn't resolve this at module scope.

## Fix: Environment Variable Pattern

Replace hardcoded module-level constants with `os.environ.get()`:

```python
# Before (broken):
START_DATE = "2021-01-01"

if __name__ == "__main__":
    # trying to override via CLI arg → global scope hell

# After (fixed):
import os
START_DATE = os.environ.get("BT_START", "2021-01-01")
END_DATE   = os.environ.get("BT_END", "2025-12-31")
```

Usage: `BT_START=2025-01-01 BT_END=2026-04-30 python3 strategy.py`

Clean, works with subprocess, no scope issues.

## Alternative: sys.modules hack

```python
import sys
if __name__ == "__main__":
    sys.modules["__main__"].START_DATE = args.start
```

Works but env vars are cleaner and shell-composable.

## Where this bites

Any standalone Python script that:
1. Defines module-level configuration constants
2. Wants CLI args to override them
3. Uses `if __name__ == "__main__":` as entry point

Common in: quant strategy backtests, data pipeline scripts, batch processing tools.
