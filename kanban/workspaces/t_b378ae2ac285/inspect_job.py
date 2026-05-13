#!/usr/bin/env python3
import json

data = json.load(open('/home/pebynn/.hermes/cron/jobs.json'))
for job in data:
    if 'afff56398abe' in str(job):
        print(json.dumps(job, indent=2, ensure_ascii=False))
        break
else:
    print("Job not found")
