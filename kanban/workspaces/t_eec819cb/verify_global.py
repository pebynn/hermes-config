#!/usr/bin/env python3
"""Verify global lesson edges."""
import json

data = json.load(open('/home/pebynn/brain/graphify-out/graph.json'))
nodes = data['nodes']
edges = data['links']

# Check global lesson edges
lesson_nodes = [n for n in nodes if n.get('file_type') == 'lesson' and n.get('properties',{}).get('domain') == 'global']
print(f'Global lesson nodes: {len(lesson_nodes)}')

# Check their edges
for n in lesson_nodes[:3]:
    nid = n['id']
    conn = [e for e in edges if e.get('source')==nid or e.get('target')==nid]
    print(f'\n  {nid} ({n.get("label","")[:50]})')
    for e in conn:
        print(f'    {e["source"]} --[{e.get("relation","?")}]--> {e["target"]}')

# Check ALL domain-lesson edges for completeness
print(f'\n--- All edge relations to lesson nodes ---')
lesson_ids = set(n['id'] for n in lesson_nodes)
added_edges = [e for e in edges if e.get('source') in lesson_ids or e.get('target') in lesson_ids]
print(f'Total: {len(added_edges)}')
relations = {}
for e in added_edges:
    src = e['source']
    tgt = e['target']
    rel = e.get('relation','?')
    if src.startswith('lesson_') or 'lesson' in src:
        parent = tgt
    else:
        parent = src
    relations[parent] = relations.get(parent, 0) + 1
print('Parent distribution:')
for parent, count in relations.items():
    print(f'  {parent}: {count}')
