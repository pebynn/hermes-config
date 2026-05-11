# Hindsight Repair — 2026-05-10

## Problem

Hindsight container running 41h but non-functional:
- `ModuleNotFoundError: No module named 'hindsight_embed'` → embed daemon failed
- `ModuleNotFoundError: No module named 'hindsight'` → Hermes plugin couldn't load client
- Container consumed 788MB RAM with zero functionality

## Fix

### Step 1: Install hindsight_embed
```bash
~/.hermes/hermes-agent/venv/bin/python3 -m pip install hindsight-embed
# Success: hindsight-embed==0.6.1
```

### Step 2: Old `hindsight` package uninstallable
The `hindsight` PyPI package (0.1.7) uses `use_2to3` which is removed in modern setuptools. Cannot install.

### Step 3: Compatibility Shim
Created `~/.hermes/hermes-agent/venv/lib/python3.11/site-packages/hindsight.py`:

```python
"""Bridge old Hermes plugin API → new hindsight_client"""
from hindsight_client import Hindsight as _HindsightClient

class HindsightEmbedded:
    def __init__(self, *args, **kwargs):
        self._client = None
    def connect(self, url=None, api_key=None):
        self._client = _HindsightClient(base_url=url or "http://localhost:8888")
        return True
    def retain(self, text, metadata=None):
        # ... maps to new API
    def recall(self, query, limit=5):
        # ... maps to new API

sys.modules['hindsight'] = sys.modules[__name__]
```

### Step 4: Verified Full Pipeline
- Bank created: PUT /v1/default/banks/hermes_main
- Memory retained: POST .../memories with content
- API healthy: `{"status":"healthy","database":"connected"}`

## Key Pattern

When an old PyPI package uses `use_2to3` (Python 2→3 migration tool removed in modern pip):
1. Find the NEW client package (hindsight_client==0.6.1 in this case)
2. Create a compatibility shim module wrapping the new API
3. Place it where the old import path expects it
4. No need to modify the actual plugin source

## Remaining

Gateway restart needed to pick up the shim. Currently old sessions still show the ModuleNotFoundError in agent.log, but it's a WARNING (non-fatal).
