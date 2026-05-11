# Publish Fallback Chain — 3-Tier Degradation Pattern

## Problem (2026-05-10)

publish_kepu.py was a standalone script that only had API→local_html save fallback.
When API failed (40164 IP whitelist), it skipped Cookie and Browser tiers entirely.
The sub-agent wrote a simplified version instead of extending publish_draft.py.

## Root Cause

Sub-agents bypass established infrastructure. publish_draft.py already had:
- Tier 1: API (add_draft + upload_image)
- Tier 2: Cookie直连 (requests with browser cookies)
- Tier 3: Browser自动化 (Playwright + stored session)
- Tier 4: Local HTML save (last resort)

But publish_kepu.py only implemented Tier 1 + Tier 4, skipping 2/3.

## Fix Pattern

**Always make thin wrappers, never standalone scripts.**

Correct approach:
```python
# publish_kepu.py — 薄封装
import subprocess, sys
from pathlib import Path

PUBLISH_SCRIPT = Path(__file__).resolve().parent / "publish_draft.py"
DRAFT_PATH = Path.home() / "writing-data/drafts/2026-05-11-科普.md"

subprocess.run([
    sys.executable, str(PUBLISH_SCRIPT),
    "--file", str(DRAFT_PATH),
    "--type", "kepu",
], timeout=300)
```

Anti-pattern: Copy-pasting publish logic into a new file, losing the fallback chain.

## publish_draft.py Extension

Added `--file` parameter for arbitrary draft paths (科普等非标准命名):
```
parser.add_argument("--file", type=str, help="直接指定draft文件路径")
parser.add_argument("--type", choices=["daily", "weekly", "kepu"])
```

## Verification

After fix, run `publish_kepu.py` → it delegates to publish_draft.py → full 3-tier fallback intact.
Also run `publish_draft.py --file /path/to/draft.md --type kepu` directly to test.

## Related Pitfalls

1. Sub-agent `summary` is self-report — always stat/compile/diff verify
2. Sub-agents will write new scripts instead of extending existing ones — audit for this pattern
3. Cookie fallback was nested inside `if token:` block in earlier version — ensure fallbacks are independent code paths
