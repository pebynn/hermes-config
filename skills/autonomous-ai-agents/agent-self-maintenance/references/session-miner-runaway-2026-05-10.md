# session-miner Runaway Incident (2026-05-10)

## Timeline

| Time | Event |
|:--|:--|
| 02:00 | 周度自优化 triggers massive session summarization storm → 55 rate limit (429) failures in 30 min |
| 04:38 | session-miner (8b9037f1fbdf) starts, tasked with mining 545 historical sessions |
| 04:38-15:18 | session-miner runs for **10h40m** without stopping, making 642 session_search calls |
| 05:45 | cross-domain-sync (03ca993eb819) finishes after 75min — also affected by rate limits |
| 15:18 | Manually paused via `cronjob action=pause` |

## Root Cause

session-miner uses `session_search` to feed full session transcripts to an LLM for summarization. With 545 sessions × ~3 retries per session = potentially 1600+ API calls. The design had:

- ❌ No hard timeout — ran until all sessions processed (10+ hours)
- ❌ No batch limit — tried to process ALL 545 sessions in one run  
- ❌ No rate limiting on session_search — calls fired as fast as possible
- ❌ No self-termination — no "I'm done" signal

## Cost Impact

- ~¥15-20 in DeepSeek API tokens for session-miner alone
- ~¥8-10 for 周度自优化 session summarization storm
- Total incident: ~¥30
- Discovered via DeepSeek billing dashboard, not system alerts (cost tracker shows $0.00)

## Required Fixes

✅ All fixes applied (2026-05-10 15:30):

1. **Hard timeout**: ✅ session-miner prompt rewritten with 15min timeout + 50 session batch limit + 3s rate limit between session_search calls
2. **Batch limit**: ✅ Max 50 sessions, max 5 deep-analysis
3. **Rate limiting**: ✅ session_search间隔≥3秒, 禁止递归
4. **Self-termination**: ✅ "到15分钟必须停止" as top rule
5. **Cost tracker**: ✅ Patched to estimate from message_count (was always $0.00)
6. **Cost circuit breaker**: ✅ New cron (b720fd552d39) auto-pauses session-miner + 周度自优化 if daily cost > $3.00 (~¥50)

## Related

- Cost tracker bug: `mcp_cost_guard_query_cost` reports $0.00 for everything
- 周度自优化 (15d19bd7a80f) session summarization storm at 02:00
- Session summarization 429s already filtered by watchdog as noise — but the underlying cost is real
