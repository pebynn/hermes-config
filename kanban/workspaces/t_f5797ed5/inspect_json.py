#!/usr/bin/env python3
import json
with open('/tmp/midcap_signal.json') as f:
    data = json.load(f)

print("Top-level keys:", list(data.keys()))
print()
print("pipeline:", data.get('pipeline'))
print("total_screened:", data.get('total_screened'))
print("total_industries:", data.get('total_industries'))  
print("weights:", json.dumps(data.get('weights', {}), indent=2))
print()
# Show first top20 entry structure
if data.get('top20'):
    print("First top20 entry:")
    print(json.dumps(data['top20'][0], indent=2, ensure_ascii=False))
