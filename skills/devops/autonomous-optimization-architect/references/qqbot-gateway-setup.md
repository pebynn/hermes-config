# QQ Bot Gateway Setup — Complete Guide

> Tested 2026-05-07 on Hermes Agent with DeepSeek v4-pro.

## Quick Setup (QR Scan Method)

The QQ Bot platform adapter supports QR-code scan-to-configure onboarding:

### Step 1: Install QR code dependency
```bash
pip install qrcode --break-system-packages
```

### Step 2: Create bind task + get URL
```python
import sys
sys.path.insert(0, 'gateway')
from gateway.platforms.qqbot.onboard import _create_bind_task, build_connect_url
task_id, aes_key = _create_bind_task()
url = build_connect_url(task_id)
print(url)  # → https://q.qq.com/qqbot/openclaw/connect.html?task_id=...
```

### Step 3: User scans QR with QQ app
Open the URL on phone → QQ app auto-opens → authorize the bot.
Task expires after 600s, max 3 refreshes.

### Step 4: Poll for credentials
```python
from gateway.platforms.qqbot.onboard import _poll_bind_result, BindStatus, decrypt_secret
status, app_id, encrypted_secret, user_openid = _poll_bind_result(task_id)
if status == BindStatus.COMPLETED:
    client_secret = decrypt_secret(encrypted_secret, aes_key)
    # → APP_ID, CLIENT_SECRET, USER_OPENID
```

### Step 5: Write credentials and allowlist
```bash
echo "QQ_APP_ID=<app_id>" >> ~/.hermes/.env
echo "QQ_CLIENT_SECRET=<secret>" >> ~/.hermes/.env
echo "QQ_ALLOWED_USERS=<openid>" >> ~/.hermes/.env
```

### Step 6: Restart gateway
```bash
hermes gateway stop && sleep 3 && hermes gateway start
```

### Step 7: Verify
```bash
grep "qqbot connected" ~/.hermes/logs/gateway.log
# → ✓ qqbot connected
```

## Common Issues

### "invalid appid or secret" (code 100016)
Credentials expired or wrong. Re-run QR flow for fresh credentials.
Old credentials are NOT automatically refreshed — full re-registration needed.

### "Unauthorized user" on inbound message
Set `QQ_ALLOWED_USERS=<openid>` in `~/.hermes/.env` and restart gateway.
The USER_OPENID is returned from the poll step.

### DNS "Temporary failure in name resolution" on send
Transient — QQ Bot adapter retries 3x with 1s/2s/4s backoff.
If persistent, check network connectivity to `api.sgroup.qq.com`.

### send_message tool says "Platform 'qqbot' is not configured"
The current agent session was started before qqbot was configured.
Cron jobs (fresh sessions) will work. For the current session, restart is needed.

## Credential Storage

- `QQ_APP_ID` / `QQ_CLIENT_SECRET` — in `~/.hermes/.env`
- `QQ_ALLOWED_USERS` — in `~/.hermes/.env`
- Platform registration: stored in gateway runtime state (`gateway_state.json`)
- `display.platforms: {qqbot: {}}` — in `~/.hermes/config.yaml` for session-level platform recognition

## Gateway Logs

```
INFO gateway.platforms.qqbot.adapter: Access token refreshed, expires in 5842s
INFO gateway.platforms.qqbot.adapter: WebSocket connected
INFO gateway.run: ✓ qqbot connected
INFO gateway.platforms.qqbot.adapter: Ready, session_id=...
```

## Cron Delivery

Configure cron jobs to deliver to QQ Bot:
```bash
cronjob action=update job_id=<id> deliver=qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12
```

The cron agent runs in a fresh session → picks up qqbot automatically.
Delivery goes through the gateway's platform adapter (WebSocket-based, no rate limiting like WeChat iLink).
