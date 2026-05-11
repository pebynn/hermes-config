#!/usr/bin/env python3
import json

data = json.load(open('/home/pebynn/brain/graphify-out/graph.json'))
nodes = data.get('nodes', [])
edges = data.get('edges', data.get('links', []))
print(f'Total nodes: {len(nodes)}')
print(f'Total edges: {len(edges)}')
print(f'Graph top-level keys: {list(data.keys())}')
print()
if nodes:
    print(f'Node 0 keys: {list(nodes[0].keys())}')
    print(f'Node 0 sample: {json.dumps(nodes[0], ensure_ascii=False)[:300]}')
if edges:
    print(f'Edge 0 keys: {list(edges[0].keys())}')
    print(f'Edge 0 sample: {json.dumps(edges[0], ensure_ascii=False)[:300]}')

# Count by file_type
from collections import Counter
ft = Counter(n.get('file_type', 'none') for n in nodes)
print(f'\nFile type counts: {dict(ft.most_common(20))}')

# Count labels containing 'lesson'
lesson_nodes = [n for n in nodes if 'lesson' in n.get('label', '').lower() or 'lesson' in n.get('id', '').lower()]
print(f'\nExisting lesson nodes: {len(lesson_nodes)}')
if lesson_nodes:
    for n in lesson_nodes[:5]:
        print(f'  {n["id"]}: {n.get("label", "")}')
