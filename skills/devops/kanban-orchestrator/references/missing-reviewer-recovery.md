
# Missing Reviewer Recovery Protocol

> When a round's code+finance tasks are done but no reviewer task exists. The orchestrator must: find the outputs → synthesize them into a reviewer task body → create the reviewer.

## Detection

After `hermes kanban --board <board> list`:

```python
# Map each round prefix to its 3 phases
# e.g., "R3-A" → check for code/finance/reviewer tasks
# If code+finance=done but reviewer NOT FOUND → gap detected
```

**SQL detection (cross-board):**
```sql
-- Find tasks with round prefixes in their titles, group by prefix
-- A gap exists when a prefix has done-tasks but no reviewer
```

## Output File Discovery

When no `round*_audit.json` exists (no reviewer ran), read raw output from each finance task's workspace:

```bash
# Step 1: Find all done finance tasks for the round
hermes kanban --board <board> list | grep -E "R<N>-.*finance|R<N>-.*回测|R<N>-.*OOS"

# Step 2: Locate their workspace output directories
find ~/.hermes/kanban/boards/<board>/workspaces/ -name "*.json" | grep -E "t_<id>"

# Step 3: Read each output file
cat ~/.hermes/kanban/boards/<board>/workspaces/t_<id>/<output>.json
```

**Real case (evo-a R3, 2026-05-13):**
- `t_22b1e0d7/workspace/R3_full_cycle_results.json` — 年化119.64%/胜率35.7%/Sharpe 2.32
- `t_19e658d8/workspace/oos_period_a.json` — 年化343%/胜率74.6%/MDD -0.92% ⚠️
- `t_19e658d8/workspace/oos_period_b.json` — 年化466%/胜率83.9%/MDD -0.99% ⚠️

## Synthesis into Reviewer Task Body

The orchestrator must include in the reviewer task body:

1. **Explicit paths to ALL raw output files** (not just file names — absolute paths)
2. **Known suspicious patterns** (e.g., OOS showing >300% with <1% MDD = almost certainly lookahead bias)
3. **Target metrics** for this strategy
4. **Historical context** (what previous rounds found, e.g., "R2 had 4 CRITICAL lookahead biases")
5. **Specific checks to perform** (momentum_entry, trailing_exit, T+1, slippage per a-share-lookahead-bias-checklist)

## Structural Ceiling Propagation

When a previous round's reviewer declared a structural ceiling (e.g., "LEVERAGE=1.0+monthly rebalance max ~30-50%"), the NEW round that responds to it MUST include in its task body:

1. The structural verdict and its ceiling value
2. The specific structural change being attempted (e.g., 1.5x leverage, daily rebalance)
3. A dual-reporting requirement: report raw return AND LEVERAGE=1.0 equivalent (raw/leverage_multiplier)
4. A pre-defined unreachability trigger: if L1-equiv < ceiling, strategy is structurally unreachable

**Real case (evo-c R6→R7):**
- R6 structural_verdict: ceiling = 30-50% at LEVERAGE=1.0+monthly
- R7 response: 1.5x leverage (expected raw ~43%) + daily rebalance
- R7 reviewer check: if annual_return_L1_equiv < 50%, declare structural impossibility
- This prevents infinite iteration: R6's 28.91% was already below the ceiling; R7 must show daily tuning pushes it above, or strategy is dead

## Prevention: Complete-Chain Creation

When creating a new evolution round, ALWAYS create the full code→finance→reviewer chain. Never create just code+finance and "add reviewer later" — the orchestrator cron may miss the gap for multiple ticks. Even if a previous tick missed a reviewer, create all 3 for the current round.

## Post-不可达 Salvage

When a round's reviewer declares structural impossibility, don't just stop. Extract salvageable components:

1. Factor definitions that could benefit other strategies
2. Data pipelines (kline fetching, preprocessing)
3. Risk management utilities (stop-loss engines, position sizing)
4. List these in a `output/salvageable_assets.md` for cross-strategy reuse
