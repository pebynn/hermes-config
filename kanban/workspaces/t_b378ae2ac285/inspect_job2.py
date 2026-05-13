#!/usr/bin/env python3
import json

data = json.load(open('/home/pebynn/.hermes/cron/jobs.json'))
print(f"Type: {type(data).__name__}")
if isinstance(data, list):
    print(f"Length: {len(data)}")
    print(f"First 3 keys/items:")
    for i, item in enumerate(data[:3]):
        if isinstance(item, dict):
            print(f"  [{i}]: {item.get('id', item.get('name', 'unknown'))}")
elif isinstance(data, dict):
    print(f"Keys: {list(data.keys())[:10]}")
    for k, v in list(data.items())[:3]:
        if isinstance(v, dict):
            print(f"  {k}: {v.get('id', v.get('name', 'unknown'))}")
