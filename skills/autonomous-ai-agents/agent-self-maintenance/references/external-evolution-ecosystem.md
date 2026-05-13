# External Hermes Agent Evolution Ecosystem

> Discovered 2026-05-13 via awesome-hermes-agent (0xNyk) + awesome-agent-evolution (EvoMap).
> Purpose: prevent re-research. Know what exists, what's compatible, what's dead-end.

---

## Source Lists

| List | URL | Scope |
|:--|:--|:--|
| awesome-hermes-agent | github.com/0xNyk/awesome-hermes-agent | Hermes-specific ecosystem (310 lines, reviewed 2026-04-21) |
| awesome-agent-evolution | github.com/EvoMap/awesome-agent-evolution | General AI agent evolution, memory, multi-agent |

---

## Hermes Self-Evolution Resources (awesome-hermes-agent)

### Nous Official

| Project | What | Status |
|:--|:--|:--|
| **hermes-agent-self-evolution** | DSPy + GEPA genetic evolution of prompt architectures. Research pipeline for optimizing Hermes prompts/behaviors. | Official, arXiv paper |
| **tinker-atropos** | RL training infra for fine-tuning tool-calling models on real agent trajectories. | Official, standalone |

### Community — Direct Evolution

| Project | Stars | What | Compatible? |
|:--|:--|:--|:--|
| **SkillClaw** (AMAP-ML) | 705⭐ | Auto-evolves, deduplicates, improves skill library from real session data. Post-task evolution loop. Native Hermes integration via `~/.hermes/skills`. MIT license. | ✅ Yes |
| **hermes-dojo** (Yonkoo11) | — | Monitors agent performance → identifies weak skills → auto-iterates. | ✅ Yes (beta) |
| **hermes-skill-factory** (Romanescu11) | — | Meta-skill: auto-generates reusable skills from workflows. | ✅ Yes (beta) |
| **hermes-skill-marketplace** (Lethe044) | — | Agent autonomously writes, tests, publishes new skills. | ⚠️ Experimental |

### Community — Adjacent (not direct evolution but related)

| Project | What |
|:--|:--|
| **hermes-plugins** (42-evey) | Goal management, inter-agent bridge, model selection, cost control |
| **super-hermes** (Cranot) | Meta-reasoning: agent writes better prompts for itself |
| **hermes-life-os** (Lethe044) | Detects daily patterns, learns routines |
| **hermes-incident-commander** (Lethe044) | Autonomous SRE: detection + self-healing |
| **rtk-hermes** (ogallotti) | 60-90% token reduction on shell commands via pre_tool_call output compression |

---

## EvoMap Ecosystem (awesome-agent-evolution)

### evolver — NOT SUITABLE for Hermes

| Factor | Detail | Verdict |
|:--|:--|:--|
| Runtime | Node.js ≥18 (`npm install -g @evomap/evolver`) | ❌ Python stack conflict |
| Protocol | GEP (Genome Evolution Protocol): Genes + Capsules | Concept overlap with lessons/ but incompatible format |
| Target platforms | Cursor, Claude Code, Codex, OpenClaw | ❌ No Hermes hook support |
| License | GPL-3.0, transitioning to source-available | ⚠️ Not fully open |
| Function | Prompt generator, not code patcher | Different from our code-enforced B+D layer |
| Verdict | **Do not install.** Study GEP paper for ideas only. | |

### Other EvoMap Projects

| Project | What |
|:--|:--|
| awesome-agent-swarm | Multi-agent orchestration and swarm intelligence |
| EvoMap core | AI-governed global welfare data aggregator |

---

## hermes-agent-self-evolution (Nous Research, 2.9k⭐, MIT, 100% Python)

**Core mechanism**: GEPA (Genetic-Pareto Prompt Evolution, ICLR 2026 Oral) + DSPy.
- Reads execution traces → understands WHY things fail → proposes targeted mutations
- Cost: $2-10/run, API-only, no GPU needed
- 7 commits, early stage (Phase 1/5: skill files only)

**5 Guardrails** (every evolved variant must pass):
1. Full test suite — `pytest tests/ -q` must pass 100%
2. Size limits — Skills ≤15KB, tool descriptions ≤500 chars
3. Caching compatibility — No mid-conversation changes
4. Semantic preservation — Must not drift from original purpose
5. PR review — All changes go through human review, never direct commit

**Usage**: `python -m evolution.skills.evolve_skill --skill <name> --iterations 10 [--eval-source sessiondb|synthetic]`

---

## SkillClaw (AMAP-ML, 705⭐, MIT, arXiv 2604.08377)

**Core mechanism**: Daemon mode, silent background evolution from real conversations.
- `skillclaw setup && skillclaw start --daemon` — one-time setup
- "Just chat" philosophy — zero extra effort from user
- Cross-platform: Hermes, Codex, Claude Code, OpenClaw, QwenPaw, IronClaw, PicoClaw, ZeroClaw, NanoClaw, NemoClaw
- Python 3.10+
- Chinese docs available (README_ZH.md)

**Relationship to our B+D layer**: Direct competitor. Does what bd_layer_enforce.py + lessons/ do, but with:
- Daemon automation (no manual kanban_create step)
- Cross-platform (not Hermes-only)
- arXiv paper backing
- Our advantage: graphify (136K nodes) is unique, B+D is code-enforced not text-protocol

---

## Key Papers (from awesome-agent-evolution research section)

### Core Reading (P0)
- **GEPA**: Genetic-Pareto Prompt Evolution (ICLR 2026 Oral) — Nous hermes-agent-self-evolution foundation
- **A Comprehensive Survey of Self-Evolving AI Agents** (arXiv 2508.07407) — 4-component unified framework: Input→Agent→Environment→Optimizer
- **A Survey of Self-Evolving Agents** (TMLR 2026, arXiv 2507.21046) — What/when/how to evolve, intra/inter-test-time adaptation

### Directly Applicable (P1)
- **ARTEMIS** (arXiv 2512.09108) — Semantically-aware genetic operators for agent config optimization. 13.6% on competitive programming
- **E-SPL** (arXiv 2602.14697) — Joint RL weight updates + genetic operators for system prompt evolution
- **EvoClaw** (arXiv 2603.13428, benchmark) — Performance drops from >80%→38% in continuous evolution. **Warning: evolution can degrade.**
- **Group-Evolving Agents** (arXiv 2602.04837) — Agent groups as evolutionary units with experience sharing. 71.0% SWE-bench
- **SkillClaw paper** (arXiv 2604.08377) — Collective skill evolution for AI agents

### Memory Systems (for graphify enhancement reference)
- **Mem0** (54.9k⭐) — Production long-term memory, 26% LOCOMO improvement, 91% latency reduction
- **Cognee** (17k⭐) — Knowledge graph engine, 6 lines of code to build graph. Compare with graphify approach.
- **TeleMem** (454⭐) — 19% higher accuracy, 43% fewer tokens, 2.1x speedup over Mem0 as drop-in replacement

### Degradation Detection (P2 reference)
- **EvoClaw benchmark** — Evaluating agents on continuous software evolution. Benchmark reveals evolution degrades performance.
- **Reflexion** (NeurIPS 2023, 3.1k⭐) — Verbal reinforcement learning. Agents learn from mistakes through self-reflection.

---

## Integration Assessment (2026-05-13)

### Decision: DO NOT INSTALL any external system.

| Source | Verdict | Reason |
|:--|:--|:--|
| hermes-agent-self-evolution | ❌ Don't install | GEPA needs DSPy dependency chain. Phase 1/5 only. Study paper for methodology, adapt guardrails. |
| SkillClaw | ❌ Don't install | Direct competitor to B+D layer. Our graphify+code-enforcement is differentiated. Study paper only. |
| Evolver (EvoMap) | ❌ Don't install | Node.js, GPL-3.0→source-available, no Hermes support. |
| awesome-agent-evolution | ✅ Use as reference | Paper list and project comparison is the value, not code. |

### P0 Actions (executed 2026-05-13 via kanban)
- **t_69f7cdac** (research-domain, running): Read GEPA paper + Survey. Output: mechanism summary, guardrail details, gap analysis vs P+B+C+D+N.
- **t_d4c4b652** (code-domain, todo, depends on t_69f7cdac): Adapt 5 guardrails to audit_bd_layer.py (pytest, size limits, cache compatibility, semantic drift, PR review gate mapped to L2/L3 matrix).

### P1 Actions (queued after P0)
- Read SkillClaw paper → compare with B+D layer
- Output comprehensive evolution upgrade plan

### P2 Actions (queued after P1)
- Implement lessons forgetting mechanism (decay/demote stale lessons)
- Implement evolution regression testing (EvoClaw-inspired degradation detection cron)

### Why NOT SkillClaw specifically
1. B+D layer is already code-enforced (not text protocol like the failed v1)
2. graphify (136K nodes/298K edges) is a unique asset no external tool has
3. SkillClaw's daemon model adds another runtime dependency
4. Our lessons/ + bd_layer_enforce.py + audit_bd_layer.py chain is Hermes-native
5. Study the arXiv paper (2604.08377) for methodology, not for code integration

---

## Our System vs External (detailed)

| Our Component | Closest External | Relationship |
|:--|:--|:--|
| P+B+C+D+N architecture | GEPA (ICLR 2026 Oral) | Different mechanism. GEPA→genetic; P+B+C+D+N→injection+recovery. Both valid. |
| B+D layer (bd_layer_enforce.py) | SkillClaw post-task evolution | Overlap in function. Our code-enforcement vs their daemon. |
| lessons/ (8 domains) | GEP genes.json + capsules.json | Incompatible formats. Our flat .md is simpler but less structured. |
| graphify (136K/298K) | Cognee knowledge graph engine | Graphify is unique (cross-domain full-graph). Cognee is local document-graph. |
| Kanban orchestration | — | No equivalent. Evolver's hook-based approach is fundamentally different. |
| skills system | agentskills.io open standard | Already compatible. 80+ skills. |
| audit_bd_layer.py (daily) | EvoClaw benchmark | Our audit detects B/D injection rate. EvoClaw detects evolution degradation. Complementary. |

---

## Action Items (updated 2026-05-13 15:00)

### P0 — DONE
- [x] Discover and catalog external evolution ecosystem
- [x] Comprehensive integration assessment completed
- [x] Read GEPA paper + Survey → gap analysis (gepa_survey_analysis.md)
- [x] Adapt 5 guardrails to audit_bd_layer.py (762 lines, --extended mode)
- [x] Implement lessons forgetting mechanism (decay 90d/archive 180d)
- [x] BD-layer-audit cron (6c2e69287dc7, daily 10:00) with GEPA guardrails

### P1 — KANBAN TRACKED (dispatcher auto-pickup)
- [~] t_ae9ffb59 (research-domain, running): SkillClaw论文分析 vs B+D层对比
- [ ] t_457f1d86 (code-domain, todo, parent=t_ae9ffb59): EvoClaw退化检测cron实现
- [ ] t_f7386342 (research-domain, todo, parent=t_457f1d86): 综合进化升级方案

### P2 — KANBAN TRACKED (parallel, running)
- [~] t_5eed626c (research-domain, running): Tool描述优化调研
- [~] t_48bdb336 (research-domain, running): System Prompt优化调研
- [~] t_f6de2309 (research-domain, running): 遗传算法轻量借鉴研究
- [~] t_c197c415 (code-domain, running): awesome-hermes-agent季度监控cron

### Supervision
- Cron `34b839a57e6f` (每周一 09:00, no_agent): 自动检查P1/P2进度
  - 阻塞/失败 → QQ Bot P0/P1 告警
  - 依赖就绪但未promote → P1 告警
  - 全部完成 → P3 完成通知
  - 一切正常 → 静默（零token消耗）
