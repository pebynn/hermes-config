# SkillClaw vs Hermes B+D Layer — Structured Analysis

> **Source**: SkillClaw arXiv paper 2604.08377 (Ma et al., Apr 2026)
> **Date analyzed**: 2026-05-13
> **Scope**: Collective skill evolution for AI agents in multi-user ecosystems

---

## 1. What SkillClaw Is

SkillClaw is a **post-task evolution daemon** for multi-user LLM agent ecosystems (based on OpenClaw). Its core idea: treat cross-user session trajectories as the primary signal for improving the shared skill library.

### Architecture

```
User A (trajectories) ─┐
User B (trajectories) ─┼──► SkilLClaw Evolver ──► Skill Updates ──► Shared Repository
User C (trajectories) ─┘        │                                    │
                         (pattern mining,                      (auto-sync to all users)
                          dedup, refinement)
```

### Key mechanisms

| Mechanism | Description |
|-----------|-------------|
| **Trajectory aggregation** | Collects interaction traces from all users post-task |
| **Autonomous evolver** | LLM-driven agent that analyzes trajectories for recurring patterns |
| **Pattern→Update translation** | Converts behavioral patterns into concrete skill edits (refine or extend) |
| **Shared repo + auto-sync** | Updated skills propagated system-wide with zero user effort |
| **Cross-user knowledge transfer** | One user's effective workflow becomes available to all |
| **Cumulative capability improvement** | System gets better with use over time |

### Evaluation

Tested on **WildClawBench** with Qwen3-Max, showing significant performance improvement in real-world agent scenarios even with limited interaction and feedback.

---

## 2. Our B+D Layer Architecture

```
B (Before) ── pre_kanban_create.py ──► Inject known pitfalls into task body pre-dispatch
                                         (domain + global lessons)
                                         + cost estimation + cost fuse

D (After)  ── post_kanban_complete.py ──► Extract [LESSONS] blocks from completions
                                           Write to domain-specific lesson files
                                           Dedup + promotion detection

Enforce   ── bd_layer_enforce.py ──► Unified entry point (inject / recover / wrap)

Audit     ── audit_bd_layer.py ──► GEPA 5 guardrails:
  1. Size checks (skill ≤15KB, tool desc ≤500 chars)
  2. pytest integration on changed files
  3. Cache compatibility check
  4. Semantic drift detection (--semantic)
  5. Review gate (L2/L3 decision matrix)
  + Lessons decay (90d → weight*0.5, 180d → archive)

Graphify ── skill-based KG ──► 136K nodes, community detection, GraphRAG queries
```

### Data flow

```
Task Created ──► B-layer injects lessons ──► Worker executes ──► Complete with [LESSONS]
                                                                    │
                                                              D-layer extracts & writes
                                                                    │
                                                              Lessons file (domain.md)
                                                                    │
                                                              Daily audit + decay
```

---

## 3. Comparison: What SkillClaw Does That We Do NOT

| # | SkillClaw Feature | Our Gap | Impact |
|---|-------------------|---------|--------|
| 1 | **Autonomous trajectory mining** — continuously scans real session traces for failure/success patterns | We only process explicit `[LESSONS]` blocks. No automated session log mining. | High — we miss patterns the worker didn't think to write as lessons |
| 2 | **Auto-generation of skill edits** — evolver creates or refines skills autonomously from patterns | Workers manually edit skills. Our lessons files are append-only, not auto-applied. | High — our improvement loop requires human-in-the-loop |
| 3 | **Cross-user pattern detection** — aggregates signals across N users to find shared failure modes | We have single-user context (each worker sees only its own task). | High — multi-user failure modes invisible |
| 4 | **Shared skill repository + auto-sync** — improvements propagate to all users without manual intervention | Per-domain lessons files require manual merge. No cross-profile auto-sync. | Medium — knowledge siloed by domain |
| 5 | **Cumulative improvement metrics** — quantitative tracking of skill evolution over time | No metrics on whether lessons are actually reducing error rates. | Medium — can't measure ROI of B+D |
| 6 | **Behavioral pattern analytics** — mines recurring behavioral patterns from tool usage | We only analyze explicit text lessons, not behavioral data. | Medium — behavioral patterns are richer than text |
| 7 | **Dedicated benchmark (WildClawBench)** for skill evolution | No benchmark for B+D effectiveness. | Low — nice to have, not critical |
| 8 | **Post-hoc trajectory buffer** — stores trajectories for offline analysis | No trajectory store — sessions are ephemeral. | High — lost signal after task completion |

---

## 4. What We Do Better That SkillClaw Does NOT

| # | Our Feature | SkillClaw Gap | Why It Matters |
|---|-------------|---------------|----------------|
| 1 | **Pre-task prevention (B-layer)** — inject known pitfalls BEFORE execution | Pure post-hoc — no preventative mechanism | Prevents failures before they happen, not after |
| 2 | **GEPA 5 guardrails** — size checks, pytest, cache compat, semantic drift, review gates | No audit/quality infrastructure | Ensures skill quality + code hygiene |
| 3 | **Cost control** — hard cost fuse ($8/day), cost estimation, cost warnings | No mention of cost management | Prevents runaway API costs |
| 4 | **Lessons decay & archival** — 90d weight decay, 180d archival | No concept of lesson staleness | Prevents stale/bad advice from persisting |
| 5 | **Domain-scoped lesson isolation** — global + per-domain + per-profile files | All skills in one shared repo (no scoping) | Prevents cross-domain pollution |
| 6 | **Kanban task traceability** — every lesson tied to a specific task run | No task-level traceability | Audit trail for "where did this lesson come from?" |
| 7 | **Graphify 136K-node knowledge graph** — community detection, GraphRAG queries | No structured knowledge graph | Cross-document connections and graph queries |
| 8 | **L2/L3 review gate** — decision matrix for automated vs human review | No change review process | Safety: prevents bad auto-evolutions from propagating |
| 9 | **pytest integration** — changed skills auto-run tests | No test infrastructure | Quality assurance on every change |
| 10 | **Daily audit reports** — per-domain B/D rate monitoring | No performance monitoring | Visibility into whether the evolution system is working |

---

## 5. Comparison Matrix (Dimension-by-Dimension)

| Dimension | SkillClaw | Ours (B+D) | Verdict |
|-----------|-----------|-------------|---------|
| **Timing** | Post-hoc only | Before + After | **We win** (both before and after) |
| **Automation** | Fully autonomous evolver | Human-appended lessons + scripts | **SkillClaw wins** on autonomy |
| **Signal source** | Real session trajectories | Explicit [LESSONS] text blocks | **SkillClaw wins** — richer signal |
| **User count** | Multi-user aggregation | Single-user per task | **SkillClaw wins** for scale |
| **Quality control** | None mentioned | 5 guardrails + tests + review | **We win** decisively |
| **Cost management** | None | Fuse + estimation + warnings | **We win** |
| **Knowledge persistence** | Shared skill repo | Lesson files + Graphify KG | **Tie** — different approaches |
| **Measurement** | WildClawBench benchmark | Daily audit rates | **SkillClaw wins** — quantified |
| **Scalability** | Designed for many users | Designed for single-user tasks | **SkillClaw wins** for multi-user |
| **Safety** | No gates | L2/L3 review + drift detection | **We win** |
| **Freshness** | Always updating | Decay + archival | **Tie** — both handle staleness |

---

## 6. Borrow Methodology Without Installing Their System

Here's what we can integrate into the existing B+D infrastructure without a full system rewrite:

### Priority 1: Trajectory Session Miner (High Impact, Medium Effort)

Create an automated script that periodically (e.g., daily cron) scans recent completed task runs from `kanban.db`:

- Extract summaries + metadata from completed runs (last 7 days)
- Feed into an LLM-based pattern detector that identifies recurring failure/success patterns
- Auto-generate candidate lesson suggestions as `[LESSONS]` blocks
- Present them in a review queue (user confirms before writing to lessons files)

**Implementation sketch**: `scripts/trajectory_miner.py`
```python
# cronjob: daily at 3am
# 1. query kanban.db for last 7d completed tasks with summaries
# 2. cluster similar task summaries (by domain, by failure keywords)
# 3. LLM prompt: "identify recurring patterns from these N completed task outcomes"
# 4. output candidate [LESSONS] blocks to ~/.hermes/bus/miner-candidates/
```

### Priority 2: Skill Auto-Evolution Daemon (Medium Impact, High Effort)

Create a cron-based daemon (weekly cadence) that:

- Reads all domain lesson files for lessons with frequency ≥ 2
- For each high-frequency lesson: propose a skill patch (via `skill_manage(action='patch')`)
- Questions the user via a review kanban task before applying

**Key safety**: All auto-evolutions go through the L2/L3 review gate (existing GEPA guardrail 5).

### Priority 3: Cross-Task Pattern Analytics (Medium Impact, Low Effort)

Add a pre-complete hook that, before `kanban_complete`, reviews the current task's context against the last 20 completed tasks in the same domain:

- Flags when similar failures were previously encountered
- Suggests known solutions from past lessons
- Outputs a "lessons-missed" advisory if the pattern matches an existing lesson

### Priority 4: Behavioral Pattern Mining (High Impact, High Effort)

If session logs are retained (check `~/.hermes/sessions/`):

- Scan session transcript chunks for recurring tool call patterns that fail
- Cluster tool-call sequences by similarity
- Flag pattern: "Users who called tool X with params {A, B} failed 40% of the time — consider parameter validation or a wrapper skill"

### Priority 5: Cumulative Improvement Dashboard (Low Impact, Low Effort)

Add metrics to the daily audit report:

- `b_rate` trend over 7 days (is B-layer adoption improving?)
- `d_rate` trend (are workers remembering to write lessons?)
- Lesson count growth per domain
- Decay/archive activity

---

## 7. Architecture Diagram (B+D + Borrowed SkillClaw Concepts)

```
┌─────────────────────────────────────────────────────────┐
│                     TASK LIFECYCLE                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Pre-task]                                              │
│  B-layer: inject lessons ──► pre_kanban_create.py        │
│  ↑                                                       │
│  [New] Cross-task pattern checker ── "seen this before?" │
│                                                          │
│  [During task]                                           │
│  Worker executes with injected context                    │
│                                                          │
│  [Post-task]                                             │
│  D-layer: extract [LESSONS] ──► post_kanban_complete.py  │
│                                                          │
│  [New] Trajectory miner (daily cron)                     │
│  └─► Scan kanban.db for completed runs                   │
│  └─► LLM pattern detection ──► candidate lessons          │
│  └─► Review queue ──► user confirms ──► lessons file     │
│                                                          │
│  [New] Skill auto-evolution daemon (weekly)              │
│  └─► Read high-freq lessons                              │
│  └─► Propose skill patches                               │
│  └─► L2/L3 review gate check                             │
│  └─► Apply (with user review)                            │
│                                                          │
│  [Ongoing]                                               │
│  GEPA 5 guardrails (audit_bd_layer.py)                   │
│  Lessons decay (90d→weight*0.5, 180d→archive)            │
│  Graphify KG (136K nodes)                                │
│  Daily audit report                                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 8. Actionable Recommendations (Ordered by Effort/Impact)

| Priority | Action | Effort | Impact | Notes |
|----------|--------|--------|--------|-------|
| **P0** | Build trajectory_miner.py (daily cron, scan kanban.db for pattern extraction) | 1-2d dev | High | Directly closes the biggest gap — automated lesson discovery |
| **P0** | Add cross-task pattern checker hook before kanban_complete | 0.5d | High | Prevents repeat failures on the same domain |
| **P1** | Implement cumulative improvement dashboard metrics in audit_bd_layer.py | 0.5d | Medium | Measures whether B+D actually improves things |
| **P1** | Retain session trajectories for offline analysis (trajectory store) | 1d config | High | Enables full behavioral pattern mining |
| **P2** | Build skill auto-evolution daemon (weekly cron) | 2-3d dev | Medium | Fully autonomous evolution with safety gates |
| **P3** | Behavioral pattern mining from session tool-call logs | 3-5d | High | Requires trajectory store first (P1) |
| **P3** | Design and run a B+D effectiveness benchmark | 2d | Medium | Needed for quantifying ROI |

### Critical Path (Phased Rollout)

```
Phase 1 (this week):   Trajectory miner + cross-task pattern checker
Phase 2 (next week):   Cumulative dashboard + trajectory store
Phase 3 (next sprint): Skill auto-evolution daemon
Phase 4 (future):      Full behavioral pattern mining + benchmark
```

---

## 9. Summary

**SkillClaw excels at**: Automated, post-hoc, multi-user skill evolution from real interaction data.
**We excel at**: Pre-task prevention, quality guardrails, cost control, and structured knowledge management.

The systems are **complementary** rather than competing. SkillClaw is a post-task evolver; our B+D is a before+after lifecycle with safety infrastructure. The most impactful borrow is **automated trajectory mining** — closing the gap between our explicit [LESSONS] approach and their implicit pattern discovery — while keeping our **5 guardrails** and **cost controls** intact.

---

[LESSONS]
- level: 🔴 CRITICAL
  domain: research-domain
  content: SkillClaw trajectory mining gap — our [LESSONS] extraction is purely manual; we miss patterns workers don't explicitly write. Need automated trajectory mining from kanban.db.
  context: SkillClaw paper analysis revealed autonomous evolver can discover patterns from session trajectories that our explicit [LESSONS] mechanism misses. Biggest architectural gap in our B+D layer.
- level: 🟡 WARNING
  domain: research-domain
  content: SkillClaw arXiv PDF download fails via arXiv CDN — timeout on curl and wget. Use arXiv API or HTML abstract as fallback when PDF extraction fails.
  context: Attempted to fetch 2604.08377 PDF multiple times (curl, wget, Python urllib) — all timed out at 30-90s. arXiv HTML version unavailable. Had to rely on abstract page HTML + Semantic Scholar API.
- level: 🟢 INFO
  domain: research-domain
  content: B+D layer comparison template established for future paper vs system analysis — structured comparison matrix with borrow/borrow-not recommendations.
  context: First time doing SkillClaw vs B+D systematic comparison. Template can be reused for future academic paper analyses.
