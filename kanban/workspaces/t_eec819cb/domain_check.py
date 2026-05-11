#!/usr/bin/env python3
"""Quick domain node lookup."""
import json

data = json.load(open('/home/pebynn/brain/graphify-out/graph.json'))
nodes = data['nodes']

# Find domain lesson file nodes
domain_nodes = [n for n in nodes if n.get('source_file','').startswith('lessons/') and n.get('file_type')=='document']
print('Domain file nodes from lessons/:')
for n in domain_nodes:
    print(f'  {n["id"]} — "{n.get("label","")}" (source: {n.get("source_file","")})')

# Also find hermes_orchestrator
orch = [n for n in nodes if n.get('id') == 'hermes_orchestrator']
if orch:
    print(f'\nhermes_orchestrator label: "{orch[0].get("label","")}"')
