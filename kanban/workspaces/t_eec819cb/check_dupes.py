#!/usr/bin/env python3
"""Check for duplicate global lesson nodes."""
import json

data = json.load(open('/home/pebynn/brain/graphify-out/graph.json'))
nodes = data['nodes']

# Old-style lesson nodes (file_type=document, from earlier syncs)
old_lesson = [n for n in nodes if n.get('id','').startswith('lesson_') and n.get('file_type')=='document']
print(f'Old style lesson_* (document type): {len(old_lesson)}')
for n in old_lesson:
    print(f'  {n["id"]}: {n.get("label","")[:60]}')

# New-style lesson nodes (file_type=lesson)
new_lesson = [n for n in nodes if n.get('file_type')=='lesson' and n.get('id','').startswith('lesson_')]
print(f'\nNew style lesson_* (lesson type): {len(new_lesson)}')
for n in new_lesson:
    print(f'  {n["id"]}: {n.get("label","")[:60]}')

# Check if ANY labels overlap between old and new
old_labels = {n.get('label','') for n in old_lesson}
new_labels = {n.get('label','') for n in new_lesson}
overlap = old_labels & new_labels
print(f'\nOverlapping labels: {len(overlap)}')
for l in overlap:
    print(f'  "{l}"')
