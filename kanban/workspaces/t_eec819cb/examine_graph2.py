#!/usr/bin/env python3
"""Examine the graph structure for lesson-related nodes."""
import json
from collections import Counter

data = json.load(open('/home/pebynn/brain/graphify-out/graph.json'))
nodes = data.get('nodes', [])
edges = data.get('links', [])

print(f'Total nodes: {len(nodes)}, Total edges: {len(edges)}')

# Find lesson-related nodes
lesson_nodes = [n for n in nodes if 'lesson' in n.get('label','').lower() or 'lesson' in n.get('id','').lower()]
print(f'\nAll lesson-related nodes: {len(lesson_nodes)}')
for n in lesson_nodes:
    ft = n.get('file_type','')
    if ft != 'code':
        print(f'  [{ft}] {n["id"]}: {n.get("label","")[:100]}')

# Document nodes with 'lesson' in source_file
doc_lesson = [n for n in nodes if n.get('file_type')=='document' and 'lesson' in n.get('source_file','').lower()]
print(f'\nDocument nodes from lesson files: {len(doc_lesson)}')
for n in doc_lesson[:15]:
    print(f'  {n["id"]}')
    print(f'    label: {n.get("label","")[:100]}')
    print(f'    source: {n.get("source_file","")}')
    
    # Find connected edges
    nid = n['id']
    conn = [e for e in edges if e.get('source')==nid or e.get('target')==nid]
    print(f'    edges: {len(conn)}')
    for e in conn[:3]:
        print(f'      {e["source"]} --[{e.get("relation","?")}]--> {e["target"]}')
    print()

# What about document nodes from lessons/ directory?
from pathlib import Path
lessons_dir = Path('/home/pebynn/.hermes/lessons')
lesson_files = list(lessons_dir.glob('*.md'))
print(f'\nLesson files on disk: {len(lesson_files)}')
for f in lesson_files:
    print(f'  {f.name}')

# Do these appear in the graph?
for f in lesson_files:
    rel = str(f.relative_to(Path('/home/pebynn/.hermes')))
    matching = [n for n in nodes if n.get('source_file','').endswith(rel)]
    if matching:
        print(f'  {f.name}: {len(matching)} nodes in graph')
        for n in matching[:2]:
            print(f'    [{n["file_type"]}] {n["id"]}: {n.get("label","")[:80]}')
    else:
        print(f'  {f.name}: NOT in graph')
