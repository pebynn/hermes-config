#!/usr/bin/env python3
import json
with open('/home/pebynn/.pdd_auth.json') as f:
    data = json.load(f)
print('Keys:', list(data.keys()))
print('Cookies:', len(data.get('cookies', [])))
for c in data.get('cookies', [])[:8]:
    print(f'  {c.get("name","?")}: {c.get("value","")[:40]} domain={c.get("domain","?")}')
origins = data.get('origins', [])
print('Origins:', len(origins))
# Check for MMS_SESS token
for c in data.get('cookies', []):
    if c.get('name') in ('MMS_SESS', 'PASS_ID'):
        print(f'  KEY {c["name"]}: {c["value"][:50]}...')
