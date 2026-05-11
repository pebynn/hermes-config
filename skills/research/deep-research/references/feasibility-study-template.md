# Technical Feasibility Study Template

Use this structure when researching "Can X work for Y?" or "Should we use A or B for Z?" — questions where the answer is a go/no-go decision, not open-ended analysis.

## When to Use

Feasibility study is the right format when:
- The question is bounded: a specific tool/approach applied to a specific problem
- Existing approaches are known to fail (blocking points are documented)
- The output needs a clear recommendation with confidence level
- Engineering tradeoffs (not just research insights) are the primary value

For open-ended exploration ("what are the trends in X?"), use the full 9-lens deep-research protocol instead.

## Structure

### 1. Core Component Analysis (one section per major piece)
Each component gets its own section covering:
- Availability on the target platform (install commands, version verification)
- Core mechanism (how it works at the technical layer that matters)
- Compatibility with other components in the stack
- Known defects and their mitigations

### 2. Bypass/Blocking Analysis
If the research is about bypassing an existing system:
- Document the layers of defense (first layer, second layer, third layer)
- For each layer, explain WHY the proposed approach bypasses it
- Use flow diagrams showing the event/data path through all layers
- Include a table of blocking points with their resolution status

### 3. Positioning/Interaction Strategy
If the system interacts with UI:
- OCR accuracy expectations by element type (table format)
- Template matching as alternative/primary
- Hybrid strategy ranking (priority order of positioning methods)
- Comparison table vs the existing CSS-selector approach

### 4. Comprehensive Comparison
- Table comparing old approach vs proposed approach across all relevant dimensions
- Each dimension gets a star rating or status indicator
- The "winner" per dimension is explicit
- A risk matrix: what could go wrong, severity, mitigation

### 5. Hybrid/Mixed Approach
Rarely is the answer "replace everything with X." Design a mixed approach:
- Which phases use the old approach (it still works there)
- Which phases use the new approach (only where needed)
- Pseudocode showing the handoff between approaches
- Phase-by-phase implementation roadmap with time estimates

### 6. Conclusion
- A single-word answer: Feasible / Conditionally Feasible / Not Feasible
- Confidence level (percentage)
- The ONE sentence summary a decision-maker needs
- Immediate next step (often: test the lightest-weight alternative first)

## Research Methodology

1. **Parallel burst first**: Decompose into 4-8 sub-topics, search all simultaneously
2. **Extract the best 2-3 URLs per topic**, not all of them
3. **Read existing code/infra** before searching — it contains the blocking points
4. **Every technical claim gets a source URL** — this is a decision document
5. **Prefer primary sources** (manpages, official docs, source code) over blog posts

## Pitfalls

- Don't make the report longer than needed. 500-800 lines for a 5-component study is the sweet spot.
- Don't skip the "lightest alternative first" recommendation. In the case of OS-level automation: always test CDP Input first before committing to Xvfb+PyAutoGUI.
- Don't present a single-lens analysis as conclusive. The comparison matrix should show both approaches losing on some dimensions.
- If you can't find a source for a claim, downgrade it to "unverified assumption" in the text.
