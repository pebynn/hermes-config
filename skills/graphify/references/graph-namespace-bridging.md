# Graph Namespace Bridging (brain:: ↔ .hermes::)

## Problem

Hermes knowledge graph has two independent namespaces:
- **brain::** — from `~/brain/soul/` (graphify-daily cron)
- **.hermes::** — from `~/.hermes/` (graphify on hermes config)
- **hermes (no prefix)** — from `~/.hermes/` older runs

These namespaces are DISCONNECTED. `graph_find_path` between them returns "No path".
graph_search works fine (global), but path traversal within a single namespace fails.

## Diagnosis

```bash
# Check if brain→.hermes path exists
mcp_graphify_graph_find_path(source="brain::brain_global_lessons", target=".hermes::hermes_writing-domain")
# → "No path found" = namespaces disconnected
```

## Three-Layer Bridge Strategy

### Layer 1: brain:: → hermes (no prefix)

Bridge brain knowledge concepts to their hermes namespace equivalents:

```python
bridges = [
    ("brain::brain_global_lessons", "global_lessons", "equivalent_to"),
    ("brain::brain_financedomain_lessons", "finance_domain", "equivalent_to"),
    ("brain::brain_writingdomain_lessons", "writing_domain", "equivalent_to"),
]
```

### Layer 2: hermes → .hermes::

Bridge the intermediate namespace to the dotted namespace:

```python
bridges = [
    ("writing_domain", ".hermes::hermes_writing-domain", "equivalent_to"),
    ("finance_domain", ".hermes::hermes_finance-domain", "equivalent_to"),
    ("code_domain", ".hermes::hermes_code-domain", "equivalent_to"),
    ("ops_domain", ".hermes::hermes_ops-domain", "equivalent_to"),
    ("research_domain", ".hermes::hermes_research-domain", "equivalent_to"),
    ("ec_domain", ".hermes::hermes_ec-domain", "equivalent_to"),
]
```

### Layer 3: global_lessons → domain nodes

Bridge the global lessons hub to individual domain nodes:

```python
bridges = [
    ("global_lessons", "writing_domain", "applies_to"),
    ("global_lessons", "finance_domain", "applies_to"),
    ("global_lessons", "code_domain", "applies_to"),
    ("global_lessons", "ops_domain", "applies_to"),
    ("global_lessons", "research_domain", "applies_to"),
    ("global_lessons", "ec_domain", "applies_to"),
]
```

### Full bridge script

```python
import json
from pathlib import Path

graph_path = Path.home() / 'brain' / 'graphify-out' / 'graph.json'
g = json.loads(graph_path.read_text())
edges = g['links']
nodes = {n['id'] for n in g['nodes']}

bridges = [
    # L1: brain → hermes
    ("brain::brain_global_lessons", "global_lessons"),
    ("brain::brain_financedomain_lessons", "finance_domain"),
    ("brain::brain_writingdomain_lessons", "writing_domain"),
    ("brain::concept_Wiki_节点___Skills_映射", ".hermes::hermes_llm-wiki"),
    # L2: hermes → .hermes::
    ("writing_domain", ".hermes::hermes_writing-domain"),
    ("finance_domain", ".hermes::hermes_finance-domain"),
    ("code_domain", ".hermes::hermes_code-domain"),
    ("ops_domain", ".hermes::hermes_ops-domain"),
    ("research_domain", ".hermes::hermes_research-domain"),
    ("ec_domain", ".hermes::hermes_ec-domain"),
    # L3: global → domains
    ("global_lessons", "writing_domain"),
    ("global_lessons", "finance_domain"),
    ("global_lessons", "code_domain"),
    ("global_lessons", "ops_domain"),
    ("global_lessons", "research_domain"),
    ("global_lessons", "ec_domain"),
]

added = 0
for src, tgt in bridges:
    if src in nodes and tgt in nodes:
        exists = any(
            e.get('source') == src and e.get('target') == tgt
            for e in edges
        )
        if not exists:
            edges.append({
                "source": src, "target": tgt,
                "relation": "equivalent_to" if "equivalent" not in locals() else "applies_to",
                "confidence": "INFERRED",
                "confidence_score": 0.85,
                "source_file": "bridge_manual",
                "weight": 1.0
            })
            added += 1

for i, (src, tgt) in enumerate(bridges):
    if i < 4:  # L1
        edges[-added + i]["relation"] = "equivalent_to" 
    elif i < 10:  # L2
        edges[-added + i]["relation"] = "equivalent_to"
    else:  # L3
        edges[-added + i]["relation"] = "applies_to"

g['links'] = edges
graph_path.write_text(json.dumps(g, indent=2))
print(f"Added {added} bridge edges. Total: {len(edges)}")
```

## Verification

```python
import json, networkx as nx
from networkx.readwrite import json_graph

g = json.loads(Path('~/brain/graphify-out/graph.json').read_text())
G = json_graph.node_link_graph(g, edges='links')

tests = [
    ('brain::brain_global_lessons', '.hermes::hermes_writing-domain'),
    ('brain::brain_financedomain_lessons', '.hermes::hermes_finance-domain'),
]
for src, tgt in tests:
    path = nx.shortest_path(G, src, tgt)
    print(f'OK ({len(path)-1} hops)')
```

## Pitfall

⚠️ **MCP cache invalidation**: The graphify MCP server caches graph data in module-level `_graph_data`. After modifying `graph.json`, the MCP server won't see the new edges until the next session / gateway restart. Verification must use direct Python access to the JSON file, not MCP tools.

### Edge Direction

The graph is DIRECTED. Edges are only traversable source→target. For two-way connectivity, add reverse edges explicitly.
