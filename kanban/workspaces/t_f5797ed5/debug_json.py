#!/usr/bin/env python3
import json
with open('/tmp/midcap_signal.json') as f:
    data = json.load(f)
print("Top-level keys:", list(data.keys()))
print("top20 exists:", 'top20' in data)
print("top20 type:", type(data.get('top20')))
print("top20 len:", len(data.get('top20', [])))
if data.get('top20'):
    print("First top20 keys:", list(data['top20'][0].keys()))
print()
print("signals exists:", 'signals' in data)
print("signals type:", type(data.get('signals')))
print("signals len:", len(data.get('signals', [])))
