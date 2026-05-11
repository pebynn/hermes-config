---
allowed-tools:
- terminal
- read_file
- memory
- send_message
author: unknown
description: WeChat iLink Bot gateway setup for Hermes — QR login, token management,
  session expiry handling, and the session timeout workaround for outbound message
  delivery.
execution: manual
name: weixin-gateway-setup
trigger:
- user says "connect WeChat" or "setup WeChat"
- WEIXIN_TOKEN needs refresh (session expired, errcode=-14)
- cron delivery shows "platform 'weixin' not configured/enabled"
- gateway log shows "Session expired; pausing for 10 minutes"
- send_message returns errcode=-14 session timeout
version: 1.0.0
---

# WeChat iLink Gateway Setup — Hermes

## ⚠️ Recommendation: Use QQ Bot Instead

WeChat iLink has severe rate limiting (ret=-2, bursts of rejections every few minutes) and session expiry every 1-2 hours. **QQ Bot is now the recommended primary messaging channel** — it uses WebSocket, has no rate limiting, and is a first-class Hermes integration.

QQ Bot setup guide: see `autonomous-optimization-architect` skill → `references/qqbot-gateway-setup.md`

Keep WeChat as emergency backup only.

### QQ Bot Cron Deliver vs Gateway Response Path (Important Distinction)

**Gateway response path** (inbound → response): When user sends a message to QQ Bot, the gateway receives it, Hermes processes it, and the gateway sends a response back. This path is confirmed working — check gateway logs for `[QQBot] Sending response`.

**Cron deliver path** (`deliver: qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12`): Cron jobs deliver through a different mechanism — the `notify.py` script queues messages, and the Hermes delivery system dispatches them. This path may use `send_message` under the hood, which can fail with "No home channel set for qqbot" if `QQBOT_HOME_CHANNEL` is not configured. 

**Diagnosing QQ Bot cron delivery failures:**
1. Check gateway log: `grep 'qqbot' ~/.hermes/logs/gateway.log | grep -v 'WebSocket\|Reconnect\|Identify'`
2. Check if `notify.py --queue` has pending messages
3. Verify `QQBOT_HOME_CHANNEL` is set: `hermes config get QQBOT_HOME_CHANNEL`
4. Test with a manual cron run: `hermes cron run <job_id>`

## Why This Skill Exists

Hermes WeChat (weixin/iLink) connections expire every 1-2 hours. Recovery is a repeatable procedure: QR login → save token → restart gateway. There are also known limitations with outbound push that require workarounds.

## Architecture

```
.env                        # WEIXIN_TOKEN, WEIXIN_ACCOUNT_ID, WEIXIN_BASE_URL
~/.hermes/weixin/accounts/  # Session files per account:
  ├── <account>@im.bot.json              # Token + user_id + saved_at
  ├── <account>@im.bot.context-tokens.json  # Per-user session tokens
  └── <account>@im.bot.sync.json         # Sync state
~/.hermes/config.yaml       # No weixin entry needed (auto-detected from .env)
```

## QR Login (Fresh Token)

```bash
cd /home/pebynn/.hermes/hermes-agent
python3 << 'PYEOF'
import asyncio, os, sys
sys.path.insert(0, '.')
os.environ['WEIXIN_TOKEN'] = ''
os.environ['WEIXIN_ACCOUNT_ID'] = ''  # empty for new account
os.environ['WEIXIN_BASE_URL'] = 'https://ilinkai.weixin.qq.com'
from gateway.platforms.weixin import qr_login
from hermes_constants import get_hermes_home
result = asyncio.run(qr_login(hermes_home=get_hermes_home()))
if result:
    print(f"QR_URL_FOR_USER: {result.get('qrcode_url','')}")
    # Save to .env after scan completes
    import json
    print(f"TOKEN={result['token']}")
    print(f"ACCOUNT={result.get('account_id','')}")
PYEOF
```

1. Shows QR code URL + ASCII art. User scans with phone WeChat.
2. On success, saves new account files to `~/.hermes/weixin/accounts/`.

## Update .env After QR Login

```bash
# Find the latest account
ls -lt ~/.hermes/weixin/accounts/*.json | grep -v 'context-tokens\|sync'

# Extract and set
python3 << 'PYEOF'
import json, glob
files = sorted(glob.glob('/home/pebynn/.hermes/weixin/accounts/*.json'))
acct_file = [f for f in files if 'context-tokens' not in f and 'sync' not in f][-1]
d = json.load(open(acct_file))
token = d['token']
account_id = token.split(':')[0]

lines = open('/home/pebynn/.hermes/.env').readlines()
with open('/home/pebynn/.hermes/.env', 'w') as f:
    for line in lines:
        if line.startswith('WEIXIN_TOKEN='):
            f.write(f'WEIXIN_TOKEN={token}\n')
        elif line.startswith('WEIXIN_ACCOUNT_ID='):
            f.write(f'WEIXIN_ACCOUNT_ID={account_id}\n')
        else:
            f.write(line)
print(f"Token: {token[:30]}...")
print(f"Account: {account_id}")
PYEOF
```

## Restart Gateway

```bash
systemctl --user kill -s KILL hermes-gateway.service   # force if stuck
sleep 3
systemctl --user start hermes-gateway.service
sleep 10
grep -i 'weixin' ~/.hermes/logs/gateway.log | tail -5
```

Expected: `✓ weixin connected`

## Verify: Send a Test Message

Send a message to the WeChat bot from your phone. The gateway should respond. If successful, the session is active.

## Known Limitations

| Symptom | Cause | Workaround |
|---------|-------|-----------|
| `send_message` fails: errcode=-14 session timeout | iLink API doesn't support outbound push reliably; only inbound+response works | User sends any message to bot → session refreshes → use cron delivery instead of send_message |
| Session expires every 1-2 hours | iLink session TTL | Re-do QR login when needed; keep the cron delivery path as primary |
| `WEIXIN_TOKEN=***` placeholder | .env corruption or line number prefix | Strip N| prefixes: `python3 -c "import re; open('/home/pebynn/.hermes/.env','w').write(re.sub(r'^\\d+\\|','',open('/home/pebynn/.hermes/.env').read()))"` |
| Cron `last_delivery_error: Weixin send failed: Timeout context manager should be used inside a task` | aiohttp 3.13.5 `TimerContext.__enter__` (Python 3.12+) raises when `asyncio.current_task()` returns None after event loop reconnection + rate limiting. Sequence: DNS failure → poll task rebuild → iLink rate limit → chunk retry loses task context | **Fixed in code** (2026-05-03): `_api_post` in `gateway/platforms/weixin.py` catches this RuntimeError and retries via `asyncio.create_task()` to restore task context. If seeing this error again, check that the fix is present: look for `asyncio.create_task(_do_post())` in the `except RuntimeError` handler of `_api_post`. |

## Delivery Strategy

Cron jobs with `deliver: weixin:...` use the response-path (inbound-compatible), NOT send_message. They work reliably when the session is active. Always pair with a local file backup:

```
result → save to /home/pebynn/文档/多因子{date}.md
       → deliver via cron (weixin response path)
```

### Known Delivery Errors (Diagnostic Quick-Reference)

| Error Pattern | Likely Cause | Action |
|---|---|---|
| `errcode=-14 session timeout` | Session expired (1-2h TTL) | User sends any message to bot to refresh; or re-QR-login |
| `iLink sendmessage rate limited: ret=-2` | iLink rate limiting (burst send) | Auto-retry with 3x backoff built into `_send_text_chunk`. Wait 30-60s before retrying. **Common root cause**: two cron jobs firing at the same minute → concurrent send attempts → second one hits rate limit. Fix: merge same-time crons into one, or stagger by 5+ minutes. |
| `Timeout context manager should be used inside a task` | Task context loss after loop reconnect | **Should no longer occur** after 2026-05-03 fix. If seen, verify fix in `_api_post`. |
| `Cannot connect to host ilinkai.weixin.qq.com:443` | DNS / network outage (China firewall) | Gateway auto-reconnects with backoff. Check `grep 'poll error' ~/.hermes/logs/gateway.log` for frequency. |
| `iLink POST sendmessage HTTP 4xx/5xx` | Server-side error | Rare. Check gateway log for response body. Usually transient. |
