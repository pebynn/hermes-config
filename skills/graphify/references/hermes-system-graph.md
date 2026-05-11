# Hermes Agent System Knowledge Graph

Built 2026-04-30 from 139 files (114 SKILL.md + 5 SOUL.md + 5 config.yaml + 19 .py scripts).

## Graph Stats
- **736 nodes** · **1113 edges** · **43 communities**
- Token compression: **72.9x** (173,752 words → ~3,179 tokens per query)
- Cost: 28,500 input / 15,900 output tokens (LLM semantic extraction only; subagent API calls additional)
- Output: `/tmp/hermes-graph/graphify-out/`

## What's Covered
| Category | Coverage |
|----------|----------|
| 5 Domains | code-domain, ec-domain, finance-domain, ops-domain, research-domain |
| Main SOUL | Orchestrator (16 edges) — dispatches to all 5 domains |
| Skills | 114 SKILL.md files across all categories |
| Quant scripts | 19 .py files (data_common, strategies, backtest, tech screen, etc.) |
| Config | auth.json, .env, config.yaml, profile configs |

## Top-Level Architecture (God Nodes)
1. E-Commerce Domain (21) — sourcing→listing→fulfillment pipeline
2. Research Domain (18) — research→ec-domain handoff
3. Code Domain (18) — encoding/git/PR
4. Stock Analyst Domain (17) — multi-strategy quant (multi-factor, momentum, chan theory)
5. Hermes Agent Main SOUL (16) — pure scheduler/dispatcher
6. terminal (13) — most-used tool across all domains

## Key Communities
- **Hermes Core & MCP Ecosystem** (93 nodes) — core platform, MCP servers
- **API Keys & Credentials** (83 nodes) — all provider keys
- **External Platforms & Integrations** (70 nodes) — 17zwd, DeepSeek, Anthropic, etc.
- **Data Common Layer** (29 nodes) — unified data layer (data_common.py)
- **Backtest Engine** (27 nodes) — strategy backtesting
- **Mid-Cap Strategy Engine** (19 nodes) — momentum rotation + multi-factor
- **Chan Theory Analysis** (23 nodes) — 缠论 technical analysis

## How to Query
```bash
# Query the graph (BFS for broad context)
cd /tmp/hermes-graph && \
PYPATH=$(cat graphify-out/.graphify_python) && \
"$PYPATH" -c "
import json, networkx as nx
from networkx.readwrite import json_graph
from pathlib import Path
data = json.loads(Path('graphify-out/graph.json').read_text())
G = json_graph.node_link_graph(data, edges='links')
# ... then do BFS/DFS traversal
"

# Or use graphify pipeline commands:
graphify query "how does ec-domain interact with research-domain"
```
