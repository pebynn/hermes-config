#!/usr/bin/env python3
"""Final verification of the cron job config."""
import json

path = '/home/pebynn/.hermes/cron/jobs.json'
with open(path) as f:
    data = json.load(f)

jobs = data.get('jobs', [])
for job in jobs:
    if job.get('id') == 'afff56398abe':
        print(f"Job: {job['name']}")
        print(f"  Enabled: {job['enabled']}")
        print(f"  State: {job['state']}")
        print(f"  no_agent: {job['no_agent']}")
        print(f"  Script: {job['script']}")
        print(f"  Schedule: {job['schedule']['expr']} ({job.get('schedule_display')})")
        print(f"  Next run: {job['next_run_at']}")
        print(f"  Last status: {job['last_status']}")
        print(f"  Last error: {job['last_error']}")
        print(f"  Toolsets: {job.get('enabled_toolsets')}")
        print(f"  Prompt preview: {job['prompt'][:80]}...")
        print(f"\nCONFIG OK ✓")
        break
