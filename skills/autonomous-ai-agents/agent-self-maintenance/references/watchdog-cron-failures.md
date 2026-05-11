# Cron Failure Watchdog — Design Document

## Overview

`watchdog_cron_failures.py` (245 lines, `~/.hermes/scripts/`) is a zero-LLM-cost notification daemon that scans error logs for real cron failures and pushes alerts via QQ Bot.

**Cron**: `00945f068dab`, every 30 minutes, `no_agent=true`, deliver `qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12`

## Design Principles

1. **Zero token cost**: `no_agent=true` script-only cron — no LLM call, no thinking, pure Python
2. **Silent when healthy**: empty stdout → no push. Only outputs text when real errors are found
3. **Dedup by fingerprint**: SHA256 hash of error content (truncated to 16 chars). Same fingerprint not re-alerted within 30 minutes
4. **Noise filtering**: 12 known noise patterns filtered before analysis

## Noise Patterns Filtered

All 12 patterns are benign system noise, not actionable failures:

| Pattern | Source |
|:--|:--|
| `Task was destroyed but it is pending` | asyncio cleanup |
| `Task exception was never retrieved` | asyncio cleanup |
| `Connection refused.*localhost:9377` | Browser CDP port |
| `Session summarization failed.*Rate limit` | DeepSeek 429 on summary |
| `iLink sendmessage rate limited` | WeChat deprecated |
| `Weixin.*rate limited` | WeChat deprecated |
| `Temporary failure in name resolution` | DNS blip |
| `Session timed out` | QQ Bot WebSocket |
| `cannot schedule new futures after interpreter shutdown` | Shutdown race |
| `Unhandled error in exception handler` | asyncio noise |
| `No user allowlists configured` | Config warning (non-critical) |
| `Unauthorized user` | Pre-whitelist config |

## State File

`~/.hermes/data/watchdog_state.json`:
```json
{
  "last_check": "2026-05-07T21:27:17.147479",
  "alerted_fingerprints": {
    "a1b2c3d4e5f6a7b8": "2026-05-07T21:00:00"
  }
}
```

Fingerprints older than 30 minutes are auto-expired on next run.

## Alert Flow

```
errors.log (last 30min)
  → filter 12 noise patterns
  → SHA256 fingerprint each remaining ERROR
  → compare with watchdog_state.json alerted_fingerprints
  → new errors → print summary to stdout (delivered by cron to QQ Bot)
                 → call notify.py --priority P1 --title "Cron异常检测"
  → no new errors → silent exit 0
```

## Pitfalls Discovered

1. **Cron scheduler hot-reload**: After creating the watchdog cron, it showed `next_run_at` in the past but never ran. Manual execution confirmed the script works — scheduler needs gateway restart to pick up new jobs.
2. **Empty errors.log on first run**: If errors.log has no entries in the window, the script exits silently with 0. This is expected behavior.
