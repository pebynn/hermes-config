#!/usr/bin/env python3
"""Check existing global lesson nodes for dedup."""
import json

data = json.load(open('/home/pebynn/brain/graphify-out/graph.json'))
nodes = data['nodes']

# Find all lesson_* nodes (existing individual lessons)
lesson_nodes = [n for n in nodes if n['id'].startswith('lesson_') and n.get('file_type') == 'document']
print(f'Existing lesson_* nodes: {len(lesson_nodes)}')
for n in lesson_nodes:
    props = n.get('properties', {})
    h = props.get('content_hash', 'N/A') if isinstance(props, dict) else 'no properties'
    print(f'  {n["id"]}: hash={h}')
