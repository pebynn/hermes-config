# Ghost Cron: Script File Doesn't Exist

## Signature

```
last_run_at: null
last_status: null
script: "signal_a_v2.sh"
→ ls -la /home/pebynn/quant/signal_a_v2.sh → 文件不存在
```

The cron was created (likely in a previous session) but the wrapper script was never actually written to disk. The real implementation exists elsewhere.

## Diagnosis Flow

### 1. Confirm the file is missing

```bash
ls -la /path/to/referenced/script.sh
# Output: 无法访问: 没有那个文件或目录
```

### 2. Trace the origin session

Use `session_search` to find the session that created this cron:

```
session_search query="signal_a_v2 OR 策略A v2 OR 16:08"
```

Look for:
- What Python script was created
- What directory it lives in
- How it was supposed to be invoked

### 3. Find the actual implementation

The session summary will reveal the real code location. Example from 2026-05-14:

- Cron referenced: `signal_a_v2.sh` (never written)
- Real implementation: `/home/pebynn/quant/strategies/strategy_a_momentum/signal_generator.py`
- Invocation: `python3 signal_generator.py --variant full`

### 4. Create the wrapper

```bash
cat > ~/.hermes/scripts/signal_a_v2.sh << 'EOF'
#!/bin/bash
set -euo pipefail
cd /home/pebynn/quant/strategies/strategy_a_momentum
exec /home/pebynn/tools/quant_env/bin/python3 signal_generator.py --variant full
EOF
chmod +x ~/.hermes/scripts/signal_a_v2.sh
```

### 5. Update the cron

```bash
cronjob update job_id=<id> script=signal_a_v2.sh
```

## Anti-Pattern: Delete and Recreate

**Do NOT delete the cron before tracing.** Deleting loses the cron ID and any delivery/channel configuration. If you recreate it, the new cron gets a different ID, breaking any cross-reference (kanban boards, QQ Bot subscriptions, documentation).

## Root Cause

Agent in a previous session:
1. Created the Python implementation correctly
2. Set up the cron referencing a wrapper script name
3. Session ended or was interrupted before `write_file` for the wrapper completed

The wrapper script file is the last step in the chain and the most fragile — if the session ends after `cronjob create` but before `write_file`, you get a ghost cron.
