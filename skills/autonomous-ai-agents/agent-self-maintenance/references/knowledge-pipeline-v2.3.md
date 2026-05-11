# Knowledge Pipeline v2.3 — Design & Rationale

## Problem

Pre-v2.3 knowledge flow was fragmented and passive:

```
memory (bloated, 98%) ──→ lessons (manual trigger only) ──→ skills (manual) ──→ SOUL.md (drift) ──→ wiki (unsynced) ──→ graph (weekly)
```

Each hop was a break:
- Memory at 98% wasted ~1,100 tokens/round on redundant info
- Lessons only extracted when user explicitly corrected the agent
- Wiki SOUL.md copies were stale (hermes-main.md 99 lines vs actual 150+)
- Knowledge graph updated weekly — new knowledge delayed up to 7 days
- Cross-domain lesson sharing was non-existent (global.md had only 4 entries)

## Solution: 4 Daily Crons

### 04:00 `wiki-soul-sync` (script-only, zero token)
Copies SOUL.md + all profile SOUL.md → ~/brain/soul/ for gbrain indexing.
Ensures wiki and graph always reflect the latest system state.

### 03:00 `graphify-daily` (incremental update)
Changed from weekly (Monday 03:00) to daily. Knowledge graph updates every 24h instead of every 7 days.
Was: e1917ae814df schedule "0 3 * * 1"
Now: e1917ae814df schedule "0 3 * * *"

### 04:10 `session-miner` (LLM-driven)
Scans last 5 user sessions for:
- User corrections (keywords: "你又", "说了多少次", "不准", "禁止")
- Successful patterns (task completion + user approval)
- New discoveries (API paths, tool usage, config items)
Extracts lessons → writes to ~/.hermes/lessons/{domain}.md (deduplicated).

### 04:30 `cross-domain-sync` (LLM-driven)
Reads all domain lesson files, detects cross-domain applicability:
- "Data accuracy" rules → all domains → global.md
- "Pure text rules unreliable" → all domains → global.md
- "Rendering verification required" → code-domain → writing-domain, research-domain
- Writes to global.md with source domain attribution.

## Cost

| Cron | Type | Est. tokens/day |
|:--|:--|:--|
| wiki-soul-sync | Script | 0 |
| graphify-daily | LLM | ~2K |
| session-miner | LLM | ~3K |
| cross-domain-sync | LLM | ~2K |
| **Total** | | **~7K/day ($0.02/day at flash rates)** |

Negligible vs the 10x savings from main agent model downgrade ($79/month).

## Dependency Chain

```
03:00 graphify-daily     (graph DB update)
04:00 skill-learnings-sync (legacy, script-only)
04:10 session-miner       (depends: sessions must exist)
04:20 wiki-soul-sync      (depends: SOUL.md latest)
04:30 cross-domain-sync   (depends: lessons populated)
```

04:00 hour was staggered to avoid cron collision (3 crons at same minute → spread over 10-20 minutes).

## Verification

First runs pending as of 2026-05-08 04:00-04:30 window. All crons are LLM-driven with `deliver: local` (output local, no QQ notification for routine runs).
