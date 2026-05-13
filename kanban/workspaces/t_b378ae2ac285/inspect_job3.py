#!/usr/bin/env python3
import json

data = json.load(open('/home/pebynn/.hermes/cron/jobs.json'))
jobs = data.get('jobs', [])
print(f"Total jobs: {len(jobs)}")

for job in jobs:
    jid = job.get('id', '')
    if 'afff56398abe' in jid or '每日K线' in job.get('name', ''):
        print(json.dumps(job, indent=2, ensure_ascii=False))
        break
else:
    print("Job not found")
    # Print all job IDs/names for inspection
    for job in jobs[:5]:
        print(f"  {job.get('id')}: {job.get('name')}")
    print("  ...")
    for job in jobs[-5:]:
        print(f"  {job.get('id')}: {job.get('name')}")
