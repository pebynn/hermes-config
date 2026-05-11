#!/usr/bin/env python3
"""Verify the test graph."""
import json
from collections import Counter

data = json.load(open('/tmp/lessons_graph_test.json'))
nodes = data['nodes']
edges = data['links']

ft = Counter(n.get('file_type','none') for n in nodes)
print(f'File types: {dict(ft.most_common())}')

lesson_nodes = [n for n in nodes if n.get('file_type') == 'lesson']
print(f'\nLesson nodes (file_type=lesson): {len(lesson_nodes)}')

# Sample check
for n in lesson_nodes[:3]:
    print(f'  {n["id"]}')
    print(f'    label: {n.get("label","")}')
    props = n.get('properties', {}) or {}
    if props:
        print(f'    severity: {props.get("severity","")}')
        print(f'    domain: {props.get("domain","")}')
        print(f'    hash: {props.get("content_hash","")}')

# Edge count for lessons
lesson_ids = set(n['id'] for n in lesson_nodes)
lesson_edges = [e for e in edges if e.get('source') in lesson_ids or e.get('target') in lesson_ids]
print(f'\nEdges connected to lesson nodes: {len(lesson_edges)}')
for e in lesson_edges[:5]:
    print(f'  {e["source"]} --[{e.get("relation","?")}]--> {e["target"]}')

# Verify domain distribution
domains = Counter()
for n in lesson_nodes:
    props = n.get('properties', {}) or {}
    d = props.get('domain', 'unknown')
    domains[d] += 1
print(f'\nDomain distribution: {dict(domains)}')
