# Multi-Agent Patterns — 2026 Production Survival Guide

Condensed from web research (2026-05-11) covering 5 core articles + 10 search directions.

## What Survived Production (Lanham, 2026)

| Pattern | Survival | Why |
|:--|:--|:--|
| Agent-flow (pipeline) | ★★★★★ | Stage boundaries, traceable, intermediate artifacts verifiable |
| Orchestrator-Worker | ★★★★☆ | Hub fragility mitigable, translation loss controllable |
| Free-form collaboration | ★★☆☆☆ | Consensus inertia, message explosion, only survives bounded+arbitrated |

**Key quote:** "Teams of agents did not get automatically smarter than one good agent."

## The Cascade Problem

"From Spark to Fire" (2026): Hub injection → 100% system infection rate vs leaf 9.7-15.9%.
Governance layer: defense success 0.32 → >0.89, but with meaningful overhead.

**Implication for Hermes:** Commander (hub) is the single point of cascade failure. Every kanban_create routing decision must be auditable.

## Four Orchestration Patterns (MindStudio, 2026)

1. **Orchestrator-Worker** — what Hermes kanban currently is. Risk: hub bottleneck.
2. **Split-and-Merge** — parallel fan-out, merge results. Need output schema upfront.
3. **Planner-Generator-Evaluator** — adversarial loop with hard exit condition. Applicable to code+reviewer.
4. **Consensus/Debate** — multiple agents solve independently, compare. Warning: majority ≠ right (correlated errors).

## Self-Improvement: HyperAgents (2026-03-19)

Meta+UBC+Oxford+NYU paper. Key findings:
- Meta-level self-modification + open-ended exploration = sustained progress
- Removing either → stagnation
- Transferred self-improvement strategies across domains: imp@50 = 0.630 (humans: 0.0)
- **Constraint:** only works where outcomes are objectively verifiable (code compiles, math proofs, quant returns)

**For Hermes:** Safe self-evolution domains: quant factor weights, reviewer false-positive rates, EC return rates. Unsafe: writing quality, strategy planning (no clean reward signal).

## Agent Skills Architecture (arXiv:2602.12430)

Three-level progressive disclosure:
- L1: Metadata (~30 tokens, always loaded)
- L2: Instructions (200-2k tokens, loaded on trigger)
- L3: Resources (scripts, assets, loaded on explicit invoke)

**Finding:** 26.1% of community skills contain vulnerabilities. Skill Trust and Lifecycle Governance Framework proposed.

## Reliability Math

Single agent 95% → chain of 5 → 77%, chain of 10 → 60%.
Mitigations: idempotency, checkpoints, human gates at high-risk steps.
