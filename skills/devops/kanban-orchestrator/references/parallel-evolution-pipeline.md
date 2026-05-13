# Three-Strategy Parallel Evolution Pipeline (2026-05-13, updated 05-13 final)

Real case: 3 independent strategies evolved in parallel on 3 kanban boards.

## Architecture: Three Separate Boards (evo-a, evo-b, evo-c)

```
Board evo-a (Strategy A - Momentum)    Board evo-b (Strategy B - Event)      Board evo-c (Strategy C - Policy)
T1-A: code-domain ──┐                  T1-B: code-domain ──┐                T1-C: code-domain ──┐
                    ▼                                      ▼                                    ▼
T2-A: finance-domain (todo)            T2-B: finance-domain (todo)          T2-C: finance-domain (todo)
                    ▼                                      ▼                                    ▼
T3-A: reviewer (todo)                  T3-B: reviewer (todo)               T3-C: reviewer (todo)
```

All 3 boards run simultaneously. Each has a serial dependency chain:
- T1 (code): modifies strategy code, optimizes parameters/factors
- T2 (finance): runs backtest, computes annualized return/Sharpe/win rate/max DD
- T3 (reviewer): audit results, lookahead check, verdict (达标/未达标/不可达)

## Target Specification
- **年化收益率**: ≥150% (not 300% as in older docs)
- **胜率**: >45%
- **LEVERAGE**: 1.0 (铁律, never change)
- **回测区间**: 2026-01-06 ~ 2026-05-13 (fixed)

## Naming Convention
`R<N>-<A/B/C>-<阶段>` (e.g., `R1-A-代码优化`, `R2-B-回测验证`, `R3-C-结果审查`)

## Orchestrator Cron Per-Tick Logic

```
1. Check all 3 boards: hermes kanban --board evo-{a,b,c} list
2. For each strategy S (A/B/C):
   a. If reviewer=done → read output/round<N>_<s>_audit.json
      - verdict=达标 → record, no new rounds for this strategy
      - verdict=未达标 → analyze failure → create R<N+1> chain
      - verdict=不可达 → create research task (research-domain)
   b. If review=running/todo → wait (silent)
   c. If task blocked → unblock + analyze + reassign if needed
3. All 3 strategies 达标/不可达 → summary report → QQ Bot → cronjob remove
4. If any strategy still running → silent wait (next tick handles)
```

## Round N+1 Creation Protocol

Each new round creates 3 tasks: code → finance → reviewer, with dependency chain.

### Step 1: B+D wrap for code task body
```bash
python3 ~/.hermes/scripts/bd_layer_enforce.py wrap \
  --domain code \
  --title "R<N+1>-<S>-代码修复-<方向>" \
  --assignee code-domain \
  --body "..."
```

### Step 2: Create 3 tasks
```bash
CODE_ID=$(hermes kanban --board evo-<s> create "title" --assignee code-domain --body "..." \
  | grep -oP 't_[a-f0-9]+')
FIN_ID=$(hermes kanban --board evo-<s> create "title" --assignee finance-domain --body "..." \
  | grep -oP 't_[a-f0-9]+')
REV_ID=$(hermes kanban --board evo-<s> create "title" --assignee reviewer --body "..." \
  | grep -oP 't_[a-f0-9]+')
```

### Step 3: Link dependencies
```bash
hermes kanban --board evo-<s> link $CODE_ID $FIN_ID
hermes kanban --board evo-<s> link $FIN_ID $REV_ID
```

### Step 4: Reclaim dependent tasks (CRITICAL — prevents race)
```bash
# Dispatcher spawns all 3 tasks within seconds regardless of parents!
hermes kanban --board evo-<s> reclaim $FIN_ID
hermes kanban --board evo-<s> reclaim $REV_ID
# Verify: both should now show ◻ todo
hermes kanban --board evo-<s> list
```

### Step 5: Body MUST include
- R<N> failure diagnosis (from audit.json) — specific bugs get fixed, generic "optimize" produces random changes
- R<N+1> improvement direction (specific parameters/factors/logic)
- LEVERAGE=1.0 铁律
- 完成后kanban_complete

## Recovery Patterns (2026-05-13)

### Pattern 1: Worker left results in comment, task stuck at "ready"
**Symptom**: Task shows `ready` but has a detailed result comment. Worker exited without calling `kanban_complete`.
**Recovery**:
1. Read comment: `hermes kanban --board <board> show <tid> | grep -A30 "Comments"`
2. Extract metrics from comment
3. Manually complete: `hermes kanban --board <board> complete <tid>`
4. This happened 4× in one session (2 evo-c, 2 evo-b)

### Pattern 2: All 3 chain tasks spawn simultaneously
**Symptom**: After `kanban create` + `link`, all 3 tasks show ● running.
**Root cause**: `kanban create` sets status=ready, dispatcher spawns all within seconds.
**Recovery**: `hermes kanban --board <board> reclaim <finance_id>` + `reclaim <reviewer_id>`
**If reclaim partially fails** (reviewer stays running while finance reclaimed): re-run reclaim on the remaining task.

### Pattern 3: Finance ran stale code
**Symptom**: Finance task completed but results are from baseline/old code, not the R<N> optimized version.
**Root cause**: Finance spawned before code task finished (Pattern 2).
**Recovery**: Complete the stale finance task → reviewer flags it → create R<N+1> with fix.
**Prevention**: Pattern 2 fix (reclaim after creation).

### Pattern 4: Lock collision blocks kanban_complete
**Symptom**: `kanban_complete` and `kanban_block` both return "unknown id or already terminal".
**Root cause**: Parent and child tasks share same lock string.
**Recovery**: Orchestrator manually completes: `hermes kanban --board <board> complete <tid>`

## Execution Results (2026-05-13 R1)

### evo-a (Momentum)
- R1: code=running (44+ min), finance=todo, reviewer=todo
- Baseline: 年化73.46%/胜率27.8%/62.5%止损率
- Issue: 5% stop-loss too tight

### evo-b (Event-Driven) — R1 done, R2 created
- R1 code: done (expanded event sources)
- R1 finance: 年化4.77%, 胜率71.43% (7笔), NAV=1.02
  - ⚠️ Finance ran BEFORE code task completed → backtested stale code
- R1 reviewer: **NOT_MET**
  - 🔴 CRITICAL: find_event() lookahead bias (used post-announcement volume)
  - Signal→trade conversion: 123 signals → 7 trades (5.7%)
- R2 code: running (fix lookahead + lower SUE→0.5 + expand events)

### evo-c (Policy) — R1 done, R2 created
- R1 code: done (initial adaptation)
- R1 finance: 年化-34.39%, 胜率11.7%, NAV=0.8719
  - 84% stop-out rate (115/137 trades)
- R1 reviewer: **FAIL**
  - 🔴 MCP概念选股完全失效 (3次全失败)
  - 🔴 月度调仓退化为周度 (rebalance_weekly ignored)
  - 🔴 64%入场批次全部亏损
  - 双份backtest_engine.py (code drift)
- R2 code: running (fix MCP + rebalance + position sizing + code cleanup)

## 🚨 CRITICAL: Full-Chain Integrity Check Before New Rounds

Before creating ANY new evolution round, verify ALL previous rounds have complete code→finance→reviewer chains. Missing reviewers = no feedback = orchestrator blindly creates more rounds.

**Detection script (per board):**
```bash
# List all tasks, manually verify each round has all 3 phases
hermes kanban --board evo-<s> list
```

**Example gap (2026-05-13 evo-b):** R4 and R5 had code+finance tasks done but NO reviewer. The R3 reviewer verdict (STRUCTURALLY_UNSOUND → recommended STOP) was ignored, and 2 more rounds were created without any review gate. R5 confirmed the reviewer was right (-12.67%, 0% WR). If no reviewer exists for a round, create one immediately — do NOT create new evolution rounds first.

**Prevention rule:** After `kanban list`, map each round prefix (R1, R2, R3...) to its 3 tasks. Any round missing a reviewer → fill the gap BEFORE creating R<N+1>.

## Strategy Directory Mapping (real project paths)

The orchestrator tick logic references `output/round<N>_<s>_audit.json`. In this project, the actual paths are:

| Strategy | Board | Code Directory | Output Pattern |
|:--|:--|:--|:--|
| A (Momentum) | evo-a | `~/quant/strategies/strategy_a_momentum/` | `output/round<N>_a_audit.json` |
| B (Event) | evo-b | `~/quant/strategies/strategy_b_event/` | `output/round<N>_b_audit.json` |
| C (Policy) | evo-c | `~/quant/strategies/strategy_c_policy/` | `output/round<N>_c_audit.json` |

**Discovery**: `find ~/quant/strategies -name "round*_audit.json"` when standard paths fail.
The `evoS` shorthand (evo_a) does NOT match the actual strategy directory names.

## Key Lessons
1. **R2 task bodies must include R1 failure diagnosis** — generic "optimize" produces random changes. Specific bugs get fixed.
2. **Always reclaim dependent tasks after kanban create+link** — dispatcher spawns everything immediately.
3. **Protocol violation ≠ work incomplete** — always check comments before re-creating tasks.
4. **Workers consistently fail to call kanban_complete** — orchestrator must be prepared to manually complete 50%+ of tasks.
5. **Lock collisions between parent/child tasks** — orchestrator-side `kanban complete` bypasses this.
6. **Full-chain integrity before new rounds** — missing reviewers = wasted iterations (evo-b: 2 extra rounds with no gate).
