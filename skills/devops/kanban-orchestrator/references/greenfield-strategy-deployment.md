# Greenfield Strategy Deployment — Research to Kanban Pipeline (2026-05-13)

Real case: research report with 3 candidate strategies → 4 kanban boards → 7 tasks → code+backtest in parallel.

## Pattern Overview

```
Research Report (.md)
  │
  ├─→ Board: shared-deps (1 task: code-domain)
  │     Build backtest_engine + data_loader + factor_lib + risk_manager
  │
  ├─→ Board: strat-a (2 tasks: code → finance)
  ├─→ Board: strat-b (2 tasks: code → finance)
  └─→ Board: strat-c (2 tasks: code → finance)
```

All 4 code tasks start simultaneously. Finance tasks depend on their code parent (linked, set to todo). Summary cron polls all boards.

## Step-by-Step

### 1. Create directory structure
```bash
mkdir -p quant/strategies/{shared,strategy_a,strategy_b,strategy_c}/{data,cache,output}
```

### 2. Create boards FIRST (before any tasks)
```bash
hermes kanban boards create shared-deps
hermes kanban boards create strat-a-momentum
hermes kanban boards create strat-b-event
hermes kanban boards create strat-c-policy
```
**Pitfall**: `kanban create --board <slug>` fails if board doesn't exist. Create boards first.

### 3. Batch-create tasks with B+D wrap
Use `execute_code` to loop over task definitions. Each iteration:
```python
# B+D wrap
wrap = terminal(f"python3 ~/.hermes/scripts/bd_layer_enforce.py wrap --domain {domain} --body {shlex.quote(body)} --title {shlex.quote(title)} --assignee {worker}")
enriched = wrap["output"].strip()

# Create (--board BEFORE subcommand)
out = terminal(f"hermes kanban --board {board} create {shlex.quote(title)} --assignee {worker} --body {shlex.quote(enriched)}")
tid = re.search(r't_[a-f0-9]+', out["output"]).group(0)
```

### 4. Link dependencies + force todo
```python
# Link: code(parent) → finance(child)
terminal(f"hermes kanban --board {board} link {code_tid} {finance_tid}")

# CRITICAL: Set finance to 'todo' via SQL (kanban create makes it 'ready')
conn = sqlite3.connect(f"/home/pebynn/.hermes/kanban/boards/{board}/kanban.db")
conn.execute("UPDATE tasks SET status='todo' WHERE id=?", (finance_tid,))
conn.commit()
```

### 5. Create summary cron
```python
cronjob(action='create', name='汇总监控', schedule='every 10m', repeat=60,
        deliver='qqbot:XXX', toolsets=['terminal','file'],
        prompt='''检查7个任务状态→全部done汇总推QQ→自删cron
        任务清单: shared-deps:t_xxx strat-a:t_xxx→t_yyy strat-b:... strat-c:...
        规则: 全done→汇总→推QQ→cronjob remove
              有blocked→报告阻塞
              还有running/todo→静默退出''')
```

## Task Body Structure for Strategy Code Tasks

```python
body = """工作目录: /home/pebynn/quant/strategies/strategy_X/

策略: <名称> (<英文名>)

选股池: <约束条件>

因子构建: <因子列表+权重+排名方法>

调仓: <频率> | 止损: <条件>
数据: 用shared/data_loader.py和shared/factor_lib.py
风险: 用shared/risk_manager.py

约束: LEVERAGE=1.0 不修改回测区间 先读shared/确认可用接口
输出: strategy.py继承shared/backtest_engine.py基类
先pip install backtrader

完成后kanban_complete汇报代码结构。"""
```

**Key**: First line = absolute path. Include "先读shared/确认可用接口" to force dependency check.

## Task Body Structure for Backtest Tasks

```python
body = """工作目录: /home/pebynn/quant/strategies/strategy_X/

运行策略回测并汇报指标:
1. 确认父任务代码已完成: ls strategy.py
2. pip install backtrader pandas numpy openpyxl
3. 运行: python strategy.py
4. 输出 output/backtest_results.json
5. 验证: IC检查(IC<0.03警告) 参数不超过5个 流动性检查
6. 在kanban_complete的summary汇报: 年化/夏普/回撤/胜率/交易次数

回测区间: 2021-01-01至2025-12-31
目标: 年化X% 胜率X% 回撤<25%
约束: LEVERAGE=1.0 只用stock-sdk数据
完成后kanban_complete"""
```

## Race Condition: todo ≠ not-dispatched

**Problem**: 3 finance workers spawned despite status=todo. Sequence:
1. `kanban create` → status=ready, no parents
2. `kanban link` → adds parents field
3. `UPDATE tasks SET status='todo'` → may be too late

Dispatcher polls every 10s. If it picks up the task between step 1 and step 3, the worker spawns. Mitigation: accept this — the worker will start, check parent status, and either wait or exit. The kanban status will still show 'todo'. Check `ps aux | grep kanban` vs `hermes kanban list` to detect the gap.

## Pitfall: Workers Don't Consume Shared Dependencies

Strategy B worker duplicated data_loader.py, factor_lib.py, risk_manager.py in its own directory instead of importing from `shared/`. Strategy C worker copied the entire shared/ directory into its own tree. Root cause: task body says "用shared/" but workers may still duplicate code if they can't resolve imports.

**Prevention in task body**:
```
数据: 从 shared/ 导入，禁止在本地复制。验证: import shared.backtest_engine 必须成功。
如shared/模块未完成，等待并重试，不要自己重写。
```

## Pitfall: Done ≠ Output Produced

**Problem**: Strategy C's finance task shows `done` but `output/backtest_results.json` is empty — no file exists. Worker claimed completion without producing results.

**Detection**: After all tasks done, verify output files exist:
```bash
for d in strategy_a_momentum strategy_b_event strategy_c_policy; do
  ls -la quant/strategies/$d/output/backtest_results.json 2>&1
done
```

**Recovery**: Check task comments for error messages, then re-create the backtest task if no output found.

## Results Summary (2026-05-13)

| Strategy | Annual | Sharpe | DD | Win Rate | Trades | Verdict |
|:--|:--|:--|:--|:--|:--|:--|
| A 主力资金动量 | 73.46% | 2.08 | -22.17% | 27.8% | 1,785 | 收益✓ 胜率✗ |
| B 事件驱动 | 9.61% | 0.34 | -7.85% | 62.96% | 135 | 胜率✓ 收益✗ |
| C 政策概念 | — | — | — | — | — | 无产出 |

Shared deps: 9 files, 2,200 lines. Backtest engine + data loader + factor lib + risk manager + tests.
