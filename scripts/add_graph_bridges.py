#!/usr/bin/env python3
"""Add bridge edges connecting global lessons to all domain lesson nodes in the graph."""
import json, time, shutil, sys

GRAPH_PATH = '/home/pebynn/.hermes/graphify-out/graph.json'

# Backup
backup_path = f'{GRAPH_PATH}.audit_backup_{int(time.time())}'
shutil.copy2(GRAPH_PATH, backup_path)
print(f"Backup: {backup_path}")

with open(GRAPH_PATH) as f:
    g = json.load(f)

nodes = g['nodes']
links = g['links']

id_to_idx = {}
for i, n in enumerate(nodes):
    id_to_idx[n['id']] = i

source = 'lessons_global_global_lessons'
targets = [
    'lessons_writing_domain_writing_domain_lessons_a',
    'lessons_finance_domain_finance_domain_lessons',
    'lessons_ops_domain_ops_domain_lessons',
    'lessons_code_domain_code_domain_lessons',
    'lessons_research_domain_research_domain_lessons',
    'lessons_ec_domain_ec_domain_lessons',
]

new_links = []
for tid in targets:
    if source in id_to_idx and tid in id_to_idx:
        new_links.append({
            "relation": "conceptually_related_to",
            "context": "bridge",
            "confidence": "INFERRED",
            "source_file": "lessons/global.md",
            "source_location": None,
            "weight": 0.8,
            "confidence_score": 0.85,
            "source": source,
            "target": tid,
        })
        print(f"Bridge: {source} → {tid}")

links.extend(new_links)
print(f"Added {len(new_links)} bridge edges, total links: {len(links)}")

with open(GRAPH_PATH, 'w') as f:
    json.dump(g, f, ensure_ascii=False)

print("Done")
