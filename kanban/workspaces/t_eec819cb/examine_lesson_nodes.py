#!/usr/bin/env python3
"""Examine existing individual lesson nodes to understand their exact structure."""
import json

data = json.load(open('/home/pebynn/brain/graphify-out/graph.json'))
nodes = data.get('nodes', [])
edges = data.get('links', [])

# Find individual lesson nodes (not domain-level file nodes)
individual_lessons = [n for n in nodes if n.get('id','').startswith('lesson_')]
print(f'Individual lesson nodes (lesson_*): {len(individual_lessons)}')
for n in individual_lessons:
    print(f'\n  id: {n["id"]}')
    for k, v in n.items():
        if k != 'id':
            print(f'    {k}: {v}')
    # Find connected edges
    nid = n['id']
    conn = [e for e in edges if e.get('source')==nid or e.get('target')==nid]
    if conn:
        print(f'    edges ({len(conn)}):')
        for e in conn:
            print(f'      {e["source"]} --[{e.get("relation","?")}]--> {e["target"]}')
    print()
