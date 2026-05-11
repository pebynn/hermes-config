# Notification Channels (2026-05-08 Update)

## Current Architecture

**Primary delivery: QQ Bot (Hermes gateway, WebSocket)**

All 31 cron jobs delivering to users route through `qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12`.
PushPlus and Server酱 were removed 2026-05-08 (never functional: PushPlus needed real-name verification, Server酱 was never configured).

## Channel Comparison

| Channel | Status | Method | Rate Limit | Notes |
|:--|:--|:--|:--|:--|
| **QQ Bot** | ✅ Active | Hermes gateway WebSocket | High | Official QQ Bot API, rich message support |
| **WeChat iLink** | ⚠️ Legacy, deprioritized | Internal gateway | Severe (-2 errors) | Keep for emergency only; rate-limited |
| **PushPlus** | ❌ Removed 2026-05-08 | HTTP POST | — | Needed real-name verification (never completed) |
| **Server酱** | ❌ Never configured | HTTP POST | — | No SendKey obtained |

## Script-Level Delivery

`notify.py` (~/.hermes/scripts/notify.py) handles P0/P1 immediate alerts:

1. Writes notification to `~/.hermes/notify_queue/` (file-based queue)
2. cron agents pick up and deliver via QQ Bot
3. No external webhooks (PushPlus/Server酱 removed)

## Cron Delivery

The Hermes cron scheduler handles delivery natively via the `deliver` field:
```yaml
deliver: qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12
```
No extra configuration needed.

## Priority Routing

| Priority | Event | Channel | Timing |
|:--|:--|:--|:--|
| 🔴 P0 | Circuit breaker trip, system outage | QQ Bot immediate | Real-time |
| 🟠 P1 | Cron failure, data issue | QQ Bot + notify.py queue | Real-time |
| 🟡 P2 | Lesson promotion, pattern detected | Daily digest (QQ Bot) | 21:00 batch |
| 🟢 P3 | Task completion, routine | Daily digest (QQ Bot) | 21:00 batch |
