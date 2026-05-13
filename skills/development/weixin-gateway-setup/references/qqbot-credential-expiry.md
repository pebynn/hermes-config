# QQ Bot Credential Expiry — Full Diagnostic & Recovery

> Captured 2026-05-13: all cron deliveries down since 02:41. Root cause = expired QQ Bot app credentials.

## Error Pattern (gateway log)

```
ERROR gateway.platforms.qqbot.adapter: [QQBot:1904004298] Send failed: QQ Bot API error [500] /v2/users/A88D89DDAFEE6A7ED7EB35325B1AEA12/messages: invalid request
WARNING cron.scheduler: Job 'db99483f4cfa': live adapter send to qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12 failed (...), falling back to standalone
ERROR cron.scheduler: Job 'db99483f4cfa': delivery error: QQBot send failed: channel=400 c2c=500 group=500
```

## Diagnostic Commands

```bash
# Check when QQ Bot delivery first broke
journalctl --user -u hermes-gateway.service --since "3 days ago" 2>&1 | grep "qqbot.*Send failed" | head -1

# Check WebSocket health (connect→close loop = credential issue)
journalctl --user -u hermes-gateway.service --since "1 hour ago" 2>&1 | grep "qqbot" | grep -c "WebSocket closed"

# Check current credentials
grep -E "^QQ_" ~/.hermes/.env

# Test send to home channel (always works if bot itself is healthy)
# Use send_message tool with qqbot:F8FEB3B1529A7281750E9547DE13F1EE
# If this works but user target fails → credential expiry
```

## Root Cause Mechanism

1. QQ Bot app credentials (APP_ID + CLIENT_SECRET) have a finite lifetime
2. When they expire, the access token refresh fails → WebSocket can't connect
3. API calls to `/v2/users/{openid}/messages` return 500 "invalid request"
4. The gateway falls back to "standalone" mode (direct HTTP) which also fails
5. All 12+ cron delivery paths are dead

## After Recovery

- All cron `deliver` targets must be updated to the new openid
- `QQ_ALLOWED_USERS` in .env must be updated
- Test with `send_message` tool, verify user receives it before claiming fixed
- The `mirrored=true` flag in send_message response means message went to home channel, NOT user

## Previous Occurrences

| Date | Duration | Root Cause | Lessons |
|:--|:--|:--|:--|
| 2026-05-13 | 02:41 ~ 15:34 (5h) | Credential expiry after gateway restart cycle. Recovery delayed by: (1) snapshot secret rollback invalid after QR scan rotated credentials, (2) sed-based .env update corrupted secret value, (3) stale gateway_state.json blocked new auth | **Never restore old secret after QR scan.** QR scan = secret rotation. **Always use Python `re.sub` for .env secrets**, never sed. **Wipe gateway_state.json** before restart with new creds. |

## Key Lesson: QR Scan = Secret Rotation

When the user scans the QR code and authorizes, QQ **regenerates the bot's CLIENT_SECRET**. The old secret (including from env snapshots and git backups) becomes permanently invalid. This has two consequences:

1. If the gateway was running with the old secret during the scan, it stays connected (WebSocket token already valid) but API calls may fail
2. After gateway restart, only the QR-decrypted NEW secret works. Any attempt to restore old secrets → 100016

**Do not restore old secrets after a QR scan.** If the new secret fails, re-scan — don't fall back to backups.

## Prevention Ideas (not yet implemented)

- Weekly credential health check cron
- Monitor QQ Bot WebSocket stability (close/reopen rate > 10/hr → alert)
- Pre-expiry notification before credentials rot
