# DeepSeek API Pricing & Cache Mechanics (2026-05)

## Current Pricing (as of 2026-05-10)

| Model | Cache-Miss Input | Cache-Hit Input | Output | Notes |
|:------|:-----------------|:----------------|:-------|:------|
| V4 Pro | $0.435/M | $0.003625/M | $0.87/M | 75% discount until 2026-05-31 |
| V4 Flash | $0.14/M | $0.0028/M | $0.28/M | Standard pricing |
| V3.2 (chat) | $0.28/M | $0.028/M | $0.42/M | Standard pricing |
| V3.2 (reasoner) | $0.28/M | $0.028/M | $0.42/M | Same base as chat |

**Post-discount V4 Pro** (after 2026-05-31): cache-miss ~$1.74/M, output ~$3.48/M.
Cache-hit stays at 1/10 of cache-miss permanently (April 2026 permanent price cut).

Sources: DeepSeek official pricing page, tokenmix.ai, openai-hub.com, costgoat.com

## Cache Mechanics

### How context caching works
DeepSeek implements disk-based context caching. When identical prefix tokens appear
in consecutive requests, they're served from cache at 1/10 the price.

### Why agent conversations hit 80-90% cache
1. **System prompt reuse**: SOUL.md (~5KB), MEMORY (~2.6KB), USER PROFILE (~0.8KB)
   are identical across all turns. ~8KB of fixed prefix per turn.
2. **Multi-turn accumulation**: In a 10-turn conversation, turn 10's input includes
   all previous 9 turns as cached context. Only the newest user message is cache-miss.
3. **Skill loading**: Skills loaded via skill_view() become part of the context prefix
   and hit cache when reused across sessions.

### Calculation methodology
```
Effective input cost = cache_hit_rate × cache_hit_price + (1 - cache_hit_rate) × cache_miss_price

For V4 Pro with 85% cache hit:
  = 0.85 × $0.003625 + 0.15 × $0.435
  = $0.00308 + $0.06525
  = $0.06833/M

Old (wrong) calculation used $2.80/M → 41× overstatement on input alone
```

### Real cost comparison (calibrated 2026-05-10)

**Ground truth**: DeepSeek billing dashboard shows ¥600 ≈ $84 for 15 days (Apr 26 - May 10).

| Metric | Old (no cache, $2.80/$8.40) | Calibrated (85% cache) | Real (billing) |
|:-------|:---------------------------|:-----------------------|:---------------|
| 15-day total | $119 (30 days) | $82.56 | **$84.00** |
| Error vs real | +41% | **-1.7%** | — |
| Daily average | ~$8 | $5.50 | **$5.60** |
| Peak day | $27.70 | $18.23 | ~$18 |

Token estimation multipliers calibrated: `2800 input / 1200 output per message`
(derived from 8.1× ratio: ¥600 ÷ $10.32 initial estimate).

26,175,100 input tokens, 11,217,900 output tokens over 746 sessions.

## Lessons

1. **Never use flat input pricing for DeepSeek** — cache-hit vs cache-miss is a 10-120× difference
2. **Verify against official pricing page** rather than cached knowledge
3. **Agent workloads have unusually high cache-hit rates** due to massive system prompts
4. **Always calibrate against provider billing** — request_dump files are all failed, no real usage data
5. **Cost estimation is only as good as the calibration source** — message_count × 2800/1200 works for NOW
   but must be re-calibrated if: model changes, context slimming occurs, or V4 Pro discount expires
6. **Recalibrate after May 31** when V4 Pro 75% discount expires: cache-miss → ~$1.74/M, output → ~$3.48/M
   (will roughly double costs)
