# Pipeline-Runner Investigation Guide

## What is pipeline-runner?

`pipeline_runner.py tick` — a `no_agent: true` script cron that runs every 30 min. It:
1. Loads `~/.hermes/agenda/pipelines.json`
2. Iterates through all pipelines with `status: running`
3. Executes the current stage's script, verifies output, advances to next stage
4. Pauses on L3 stages for user decision, marks failed after 2 retries

## Job ID

`fc7f76d16dd3` — cron `*/30 * * * *`, delivers to `qqbot`.

## Diagnosis Flow

When user reports pipeline-runner errors:

1. **Check pipeline status** (not cron output — pipeline runner is no_agent):
   ```bash
   python3 ~/.hermes/scripts/pipeline_runner.py status
   ```
   
2. **Run a tick to see live output**:
   ```bash
   python3 ~/.hermes/scripts/pipeline_runner.py tick
   ```
   Exit code 0 = all pipelines stable. Exit code != 0 = check stderr.

3. **Check pipelines.json for error details**:
   ```bash
   python3 -c "import json; d=json.load(open('/home/pebynn/.hermes/agenda/pipelines.json')); [print(f'{p[\"id\"]}: {p.get(\"status\")} err={p.get(\"last_error\",\"\")[:80]}') for p in d['pipelines']]"
   ```

## Common Failure Signatures

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| `ModuleNotFoundError: No module named pandas` | Default python3 lacks quant deps | Add auto-redirect to quant_env python3 at top of script: check `sys.executable` vs target, re-exec via `subprocess.run` |
| `SyntaxError: expected 'except' or 'finally' block` | verify script was inline python with bad quoting | Move verify to a proper .py file in `~/.hermes/scripts/` |
| `[ERROR] pausing...` but no L3 in pipeline | Stage script returned non-zero exit but shouldn't have | Check stage script logic and exit codes |
| pipeline-runner tick OK but cron shows `last_status: error` | Previous tick had a failure, current tick may have auto-resolved | Just re-tick; error was historical |
| Deliver to qqbot shows tick debug messages | `print()` in script goes to stdout → delivered verbatim | Use `print("msg", file=sys.stderr)` for routine tick output |

## Fix Pattern: Python Env Auto-Redirect

When a no_agent script needs pandas/numpy from quant_env:

```python
#!/usr/bin/env python3
import sys, subprocess
from pathlib import Path

QUANT_PY = str(Path.home() / "tools" / "quant_env" / "bin" / "python3")
if sys.executable != QUANT_PY and Path(QUANT_PY).exists():
    r = subprocess.run([QUANT_PY] + sys.argv)
    sys.exit(r.returncode)

# Now pandas/numpy are available
import pandas as pd
```

This pattern is idempotent — if already running under quant_env, it skips the redirect.
