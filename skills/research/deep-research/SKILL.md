---
name: deep-research
description: Multi-lens research engine — one question, 9 angles, synthesized analysis. Uses ~/research-skill-graph/ as the knowledge base. Load this skill when given a research question and use it to produce deep, structured analysis. Invoke by saying "do deep research on [question]".
keywords: [deep-research, deep research, analysis, multi-lens, research, synthesis, strategy]
version: 1.3.0
author: Hermes Community
license: mit
related_skills:
  - last30days  # Tier 5 social sentiment — Reddit + X via last30days covers the social/anecdotal layer referenced in the 5-tier trust system (source-evaluation.md). Load this for customer, contrarian, and business lenses.
---

# Deep Research

A local research engine that takes ONE question and produces multi-angle analysis no single Google search or prompt could match.

**Knowledge base:** `~/research-skill-graph/`
**Invocations:** say "do deep research on [your question]" or "/skill deep-research" then ask your question

---

## How It Works

The system forces structured thinking through 9 research lenses, each rethinking the question from a fundamentally different angle. Lenses are defined in the skill graph folder and evolve over time.

**The 9 Lenses (in execution order):**
1. **technical** — mechanics, data, hard numbers. Strip away narrative.
2. **economic** — money flows, incentives, cost structures, who pays/profits.
3. **historical** — patterns, precedent, what failed before.
4. **business** — competitive landscape, unit economics, who's winning/losing.
5. **strategic** — key moves, leverage points, game theory. What matters in 3-10 years.
6. **customer** — real buyer vs. user, JTBD, trust signals, purchase blockers.
7. **product** — capabilities, limits, failure modes, MVPs.
8. **contrarian** — stress-test the consensus. Who benefits from the current narrative?
9. **first-principles** — rebuild from ground truth. Forget assumptions.

---

## Execution Protocol

**🔴 HARD GATE (from orchestrator SOUL.md 研究任务强制协议):** Any request containing trigger words — 研究, 分析, 调研, 策略设计, 方案设计 — MUST follow this full 9-lens protocol. The shortcut path `web_search twice → verbal conclusion` is **forbidden** at the protocol level. If you catch yourself about to take the shortcut, stop and return to Step 0.

When you receive a research question:

**Step 0 (MANDATORY):** Run `mcp_llm_wiki_wiki_search` to check existing concepts and data points for this topic. Never start from scratch — build on accumulated knowledge. This is not optional; it's the compound effect that makes the wiki work.

**Step 1:** Read the command center at `~/research-skill-graph/index.md` — it contains the full briefing template and node map.

> ⚠️ **Known discrepancy (as of 2026-05):** The lens table in `index.md` (Empirical/Historical/Comparative/Systems/Stakeholder/Causal/Uncertainty/Ethical/Synthesis) does NOT match the actual lens files on disk or the list in this SKILL.md. Use the list below (technical/economic/historical/business/strategic/customer/product/contrarian/first-principles) as authoritative. See `references/lens-alignment.md` for the fix procedure — if you can patch `index.md`, do it now.

**Step 2:** Read `methodology/research-frameworks.md` to pick the right approach for the question type:
- "Is X true?" → Verification framework
- "Why is X happening?" → Causal analysis framework
- "What happens if X?" → Scenario planning framework
- "What should I do about X?" → Decision support framework

**Step 3:** Read `methodology/source-evaluation.md` — apply the 5-tier trust system to every source:
- Tier 1: Primary data (raw datasets, peer-reviewed studies)
- Tier 2: Expert analysis (research institutions, long-form journalism)
- Tier 3: Informed commentary (expert blogs, think tank reports)
- Tier 4: General media (major news, Wikipedia — verify upstream)
- Tier 5: Social/anecdotal (Twitter, Reddit — signal detection only)

**Step 4:** Run ALL 9 lenses. For each lens:
a. Read the lens file
b. Research the topic THROUGH that lens only
c. Record findings, sources, and confidence level
d. Note contradictions with previous lenses

**Adapting lenses to domain:** For business/e-commerce/platform research topics, see `references/lens-adaptation-business.md` for guidance on reinterpreting each lens through the platform's operational dimensions.

**Step 5:** Read `methodology/contradiction-protocol.md` — resolve or document disagreements between lenses. Contradictions are features, not bugs.

**Step 6:** Read `methodology/synthesis-rules.md` — combine findings across lenses without flattening nuance.

**Step 7:** Produce all 4 output files inside `projects/[project-name]/` (directory created by orchestrator before research starts):
- **executive-summary.md** — 500 words max. What did we learn? What does it mean? What's unknown?
- **deep-dive.md** — Full analysis organized by lens, cross-references and contradictions highlighted.
- **key-players.md** — People, organizations, countries that matter most.
- **open-questions.md** — What we STILL don't know. Often more valuable than findings.

**Step 8:** Update `knowledge/concepts.md` and `knowledge/data-points.md` with everything learned.

**Pre-Completion Checklist (all must pass before research is done):**
- [ ] `mcp_llm_wiki_wiki_search` was run at Step 0
- [ ] All 9 lenses completed (no skipping)
- [ ] 4 output files present in project directory
- [ ] `knowledge/concepts.md` and `data-points.md` updated

**ANTI-PATTERN (FORBIDDEN):** `web_search` twice → verbal conclusion → done. This is a protocol violation equivalent to skipping all 9 lenses. If you catch yourself doing this, stop, go back to Step 0, and run the full protocol.

**Cost:** Research tasks have no cost limit. Run as many web_search/web_extract calls as needed. Do not shrink lens count or search depth to save tokens.

## Execution Mode (Critical)

**Orchestrator-Researcher Split:** This skill is executed by the research-domain subagent, NOT by the Hermes orchestrator. See `references/orchestrator-researcher-boundary.md` for the full flow.

**Hard Gate (SOUL.md):** The orchestrator SOUL.md contains a mandatory research protocol gate (研究任务强制协议). When the orchestrator detects research keywords (研究|分析|调研|策略|方案), it MUST: wiki_search → load deep-research → delegate to research-domain → verify 4 output files → update wiki. The orchestrator is FORBIDDEN from answering research questions directly with web_search alone. See `references/orchestrator-gate-protocol.md`.

### Parallel Topic Burst Pattern (New)

For multi-faceted topics, use a parallel burst of 4+ web_search calls covering all major sub-topics simultaneously before extracting any single result. This avoids sequential narrowing and builds a comprehensive search landscape fast.

Protocol:
1. Decompose the research question into 4-8 orthogonal sub-topics
2. Fire one web_search per sub-topic simultaneously (all in one call)
3. Scan results for the 2-3 most promising URLs per sub-topic
4. Extract those in parallel via web_extract
5. Only then begin lens-by-lens analysis

This pattern works best when the topic has clear natural axes (e.g., theory A / theory B / theory C / cross-integration), or when sources exist in multiple languages (e.g., Chinese + English). See `references/chinese-financial-research.md` for a worked example.

### Pitfall: MCP Web Search Unavailable

The protocol specifies `mcp_web_search_web_search` / `mcp_web_extract_web_extract` as the primary research tools. However, these may fail with `TAVILY_API_KEY environment variable is not set`. When this happens, fall back immediately to native `web_search` and `web_extract` tools — do not retry MCP or wait for it to start working. The native tools have the same search capability for research purposes. This is a known environment issue, not a research failure.

### Pitfall: China Firewall — Tool Accessibility Constraint

When researching tools, services, or platforms for use **inside China**, always verify whether they require a VPN/proxy to access. Many Western developer tools are blocked or severely throttled by the Great Firewall, including but not limited to: Cursor (cursor.com), Claude Code (Anthropic API), GitHub Copilot (unreliable), Docker Hub (throttled), OpenAI API. For any tool recommendation, check: (1) is the download domain accessible from China? (2) does the tool require persistent API calls to blocked endpoints? (3) is there a domestic Chinese alternative that works without VPN?

For AI coding tools specifically, see `references/china-ai-coding-tools.md` — a full landscape of 6 domestic alternatives that work without VPN, all free for personal use. Default recommendation: 通义灵码 + CodeGeeX + Fitten Code (zero-cost, zero-VPN).

For AI coding tools specifically, see `references/china-ai-coding-tools.md` — a maintained landscape of domestic alternatives (通义灵码/CodeGeeX/文心快码/Trae/Fitten Code).

When researching Chinese e-commerce topics, expect that 知乎 (zhihu.com) and similar platforms may block `web_extract` with "Failed to fetch url" errors. These are anti-scraping measures, not research failures. Mitigation: (a) prioritize non-知乎 sources when available (CSDN, 腾讯云, 搜狐, 网易, 证券时报), (b) extract 知乎 URLs one at a time if essential, (c) use search result snippets as fallback data if extraction fails. Do not retry failed zhihu extracts more than once.

For e-commerce/product-management research topics specifically, see `references/ecommerce-product-management-research.md` — a worked example covering PDD listing flows, SKU management rules, and 9-lens adaptation for platform management topics.

**DO: Live visible research for the user.**
When the user says "do deep research," they want to SEE you working — live searches, visible reasoning, real-time synthesis. Show the moves, the choices, the findings. This is how trust is built. The user can course-correct mid-stream when they can see your thinking.

**DON'T: Background delegation for Deep Research.**
Background subagent delegation via `delegate_task` has proven unreliable on some model setups — subagents can get interrupted before completing. Only use background agents after getting explicit buy-in from the user.

**Exception:** For IMPLEMENTATION after research is done (building skills, writing files), background delegation is fine — that's mechanical work, not reasoning work.

**Mid-Research Course Correction (Important Pattern):**
Occasionally a single search result or source fundamentally changes the research thesis mid-flight. Example: researching "AI agent reputation protocols" → discovers ERC-8004 already deployed Jan 2026 with identical core concept. The thesis shifts from "should you build this?" to "pivot to analytics layer on top of ERC-8004." When this happens:
1. Note the discovery explicitly ("Finding X changes the premise")
2. Adjust the remaining lenses to test the new hypothesis, not the original
3. Update the executive summary to reflect what changed and why
4. Document the shift in the deep-dive under the lens that triggered it
This is a FEATURE of live research, not a failure. The structured lens system handles the course correction gracefully.

**Payments in Crypto/Web3 Projects (Critical Rule):**
When producing a spec for any crypto or web3 product, do NOT default to Stripe, credit cards, email auth, or any fiat infrastructure — even if it seems like the obvious solution. Crypto products require crypto-native payments. Default to:
- **x402 (HTTP 402)** for API payments: wallet signature, no account, no KYC, per-request billing
- **No accounts required** for read access; anonymity is a first principle, not a feature
- **No Google Analytics** — use Plausible Analytics or a self-hosted alternative
- **No fiat on-ramps** in the spec unless explicitly requested

If Stripe or any fiat payment appears in a draft spec and the project is blockchain/crypto/web3 adjacent, it will be rejected. Confirm the payment model BEFORE including it in a spec.

---

## Critical Rules

- Each lens must RETHINK the question, not just add more information. Technical and contrarian should feel like two researchers who disagree.
- The tension between lenses IS the insight. Don't resolve it away.
- Never present a single-lens finding as a conclusion.
- Separate "what the data shows" from "what I interpret."
- [[open-questions]] is as important as [[executive-summary]].

---

## Folder Structure (lived in ~/research-skill-graph/)

```
research-skill-graph/
├── index.md                      # Command center (start here)
├── research-log.md               # All past projects with key findings
├── methodology/
│   ├── research-frameworks.md    # How to pick the right approach
│   ├── source-evaluation.md       # 5-tier trust system
│   ├── synthesis-rules.md        # How to combine findings
│   └── contradiction-protocol.md # How to handle disagreements
├── lenses/                       # The 9 research lenses
│   ├── technical.md
│   ├── economic.md
│   ├── historical.md
│   ├── business.md
│   ├── strategic.md
│   ├── customer.md
│   ├── product.md
│   ├── contrarian.md
│   └── first-principles.md
├── projects/                     # One subfolder per research project
│   └── [project-name]/
│       ├── executive-summary.md
│       ├── deep-dive.md
│       ├── key-players.md
│       └── open-questions.md
├── sources/
│   └── source-template.md        # Copy for each major source
└── knowledge/
    ├── concepts.md               # Accumulates across ALL projects
    └── data-points.md            # Verified numbers, always with attribution
```

---

## The Compound Effect

This system gets better over time:
- `knowledge/concepts.md` and `knowledge/data-points.md` accumulate across ALL projects
- After 5 projects, the AI starts with 200+ verified data points and 50+ defined concepts
- `research-log.md` tracks every project — the 10th project starts from everything already learned
- [[open-questions]] from one research become seeds for the next

---

## When to Use Each Depth Level

**Level 1 (30 min):** 3 lenses max, top 5 sources. Directional understanding.
**Level 2 (2-3 hrs):** All 9 lenses, 15-25 sources. Informed opinion backed by evidence.
**Level 3 (1-2 days):** All 9 lenses with sub-questions, 50+ sources including primary data. Publishable analysis.

**Feasibility Study (alternative format):** For bounded go/no-go questions ("Can X work for Y?"), use the structured 6-section template in `references/feasibility-study-template.md` instead of the full 9-lens protocol. The template covers component analysis, bypass mechanisms, positioning strategy, comparison matrices, hybrid approach design, and a single-word conclusion with confidence level. This format is optimized for engineering decisions, not open-ended exploration.
