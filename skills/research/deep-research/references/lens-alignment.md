# Lens Alignment: index.md Fix

## Discrepancy

The file `~/research-skill-graph/index.md` lists these 9 lenses in its table:

| # | Lens | Core Question |
|---|------|---------------|
| 1 | Empirical | What does the evidence show? |
| 2 | Historical | What is the history and trajectory? |
| 3 | Comparative | How does this compare to alternatives? |
| 4 | Systems | What are the systemic dynamics? |
| 5 | Stakeholder | Who are the actors and what do they want? |
| 6 | Causal | What causes what? |
| 7 | Uncertainty | What don't we know? |
| 8 | Ethical | What are the ethical implications? |
| 9 | Synthesis | How does it all fit together? |

But the actual lens files on disk (`~/research-skill-graph/lenses/*.md`) and the `deep-research` SKILL.md both define a different set:

| # | Lens | Core Question |
|---|------|---------------|
| 1 | technical | mechanics, data, hard numbers. Strip away narrative. |
| 2 | economic | money flows, incentives, cost structures, who pays/profits. |
| 3 | historical | patterns, precedent, what failed before. |
| 4 | business | competitive landscape, unit economics, who's winning/losing. |
| 5 | strategic | key moves, leverage points, game theory. What matters in 3-10 years. |
| 6 | customer | real buyer vs. user, JTBD, trust signals, purchase blockers. |
| 7 | product | capabilities, limits, failure modes, MVPs. |
| 8 | contrarian | stress-test the consensus. Who benefits from the current narrative? |
| 9 | first-principles | rebuild from ground truth. Forget assumptions. |

The disk files win — those are the real lens definitions.

## Fix

If you have write access to `~/research-skill-graph/index.md`, replace its lens table with the correct one above. The rest of index.md (framework, usage notes, folder structure) is fine as-is.

## Why This Happened

The research-skill-graph was initially designed with one lens taxonomy (in index.md), then later overhauled to the current 9 lenses (in the lens files). index.md was not updated to match. The SKILL.md and the lens files are the correct, living version.
