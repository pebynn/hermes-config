# E-commerce Product Management Research — Worked Example

> A step-by-step replay of applying the Level 2 deep-research protocol to an e-commerce product/platform management topic.
> Project: pdd-product-management (2026-05-03)
> Full outputs: `~/research-skill-graph/projects/pdd-product-management/`

## What makes product management research different

Product management topics sit at the intersection of platform engineering, regulatory rules, merchant user experience, and competitive strategy. The 9 lenses adapt naturally:

| Lens | E-commerce product management interpretation |
|:-----|:---------------------------------------------|
| technical | Platform architecture (React SPA/beast-core), SKU generation algorithms, form state management |
| economic | Penalty structures (保证金 deduction, deposit forfeiture), cost of compliance vs non-compliance |
| historical | Rule evolution timeline (loose→strict→balanced), policy regime shifts |
| business | Competitive comparison: PDD vs Taobao vs JD vs Douyin listing/management systems |
| strategic | Why strict SKU rules exist (price signal integrity), AI review trend, regulatory pre-positioning |
| customer | Merchant JTBD: what does a seller actually need from the listing backend? |
| product | Feature matrix: 8-step listing funnel, batch operations, review lifecycle |
| contrarian | Is "simple and merchant-friendly" narrative actually true given zero-tolerance penalties? |
| first-principles | What is the irreducible function of product listing? (digitize physical goods → enable matching) |

## Parallel Topic Burst Pattern (applied)

For platform-management topics, decompose into orthogonal sub-dimensions:

```
Question: "拼多多商品上架及商品管理全流程"
Decomposed into 8 sub-dimensions:
  1. 商品发布完整流程 (listing funnel steps)
  2. 商品管理后台操作 (dashboard operations: edit/batch/status)
  3. 规格与SKU管理机制 (spec/SKU cartesian generation & constraints)
  4. PC商家后台技术实现 (beast-core React SPA architecture)
  5. 拼多多特有商品规则 (SKU pricing red lines, penalties)
  6. 商品审核流程 (review → approve/reject → resubmit)
  7. 运营工具与诊断 (built-in + third-party analytics tools)
  8. 1688/17网选品上架对接 (sourcing platform integration)
```

Fire all 8 web_searches simultaneously → scan for top 2-3 URLs per sub-topic → extract in parallel → then lens-by-lens analysis.

## Domain Skills as Context

Always load relevant domain skills BEFORE research:
- `pdd-platform-mechanics` — platform-level knowledge (traffic structure, promotion tools, policies)
- `ec-mid-elderly-strategy` — niche-level strategy (pricing, sizing, visual design for 中老年女装)

These provide the cognitive foundation. The research fills gaps the skills don't cover — in this case, the actual listing mechanics and SKU management rules.

## Key Contradictions (Feature, Not Bug)

This research surfaced productive contradictions:
1. "Simple backend, easy to use" (product lens) vs "Zero-tolerance penalties trap newcomers" (contrarian lens)
2. "活动 is the main traffic source" (business lens) vs "Every edit triggers re-review, blocking testing agility" (customer lens)
3. "Merchants set prices freely" (economic lens) vs "SKU price gap ≤20% means platform has soft pricing power" (strategic lens)

These contradictions ARE the insight. Document them in the deep-dive under the cross-reference table.

## Pitfalls Specific to This Research Type

### Pitfall: Wiki has no prior knowledge
New/research topics often return empty wiki_search results. This is normal — start from scratch, and the research output BECOMES the wiki knowledge. Make sure to update concepts.md and data-points.md after completion.

### Pitfall: Primary sources are behind auth walls
The actual merchant backend (mms.pinduoduo.com) requires login. All direct observations come from second-hand tutorials and screenshots (Tier 3-4). Flag this uncertainty explicitly in the executive summary.

### Pitfall: CSDN articles with image-only content
Many Chinese e-commerce tutorials store critical information in images rather than text. When web_extract returns "key information is in images, not extractable," note it and move on. Don't waste calls retrying.

### Pitfall: beast-core is internal, not open-source
Technical architecture inferences about beast-core come from job postings (V2EX) rather than documentation. Mark all internal tech findings as Tier 4 (inferred) with explicit confidence levels.

## Output Quality Checklist

For e-commerce management actionable research, ensure outputs contain:
- [ ] Exact penalty amounts (not just "penalties apply")
- [ ] SKU dimension limits with specific numbers (44/60/20 thresholds)
- [ ] Review timeline expectations (48h, not "soon")
- [ ] Differentiated strategies by platform (PDD rules ≠ Taobao rules)
- [ ] Mid-niche considerations (中老年女装 SKU count overflow trap)
- [ ] Open questions categorized by verification priority (P0/P1/P2)
- [ ] Cross-lens contradiction table (the most valuable part of the deep-dive)
