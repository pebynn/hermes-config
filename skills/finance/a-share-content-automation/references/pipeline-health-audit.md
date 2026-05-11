# Pipeline Health Audit Checklist

When the writing-domain pipeline has multiple issues across sessions, or the user signals "越修越乱" — STOP patching and run this full audit first.

## Audit Dimensions (5 checks)

### 1. Cron Job Status
```bash
# Check all writing-domain cron jobs
hermes cron list | grep -E "5896e6bcea04|d075c207d860|3858ff88add6|704e9bfe5896"
```
Key fields: `last_run_at`, `last_status`, `state`, `last_error`

**Red flags**: `last_run_at: null` (never ran), `state: paused`, `last_status: error`

### 2. Script Integrity
```bash
# Verify all 6 scripts exist and pass syntax
for script in \
  .hermes/profiles/writing-domain/skills/a-share-data-collector/scripts/collect_data.py \
  .hermes/profiles/writing-domain/skills/a-share-review-writer/scripts/generate_charts.py \
  .hermes/profiles/writing-domain/skills/a-share-review-writer/scripts/generate_review.py \
  .hermes/profiles/writing-domain/skills/a-share-review-writer/scripts/weekly_summary.py \
  .hermes/profiles/writing-domain/skills/a-share-publisher/scripts/publish_draft.py \
  .hermes/profiles/writing-domain/skills/a-share-publisher/scripts/browser_publish.py
do
  python3 -c "import py_compile; py_compile.compile('$script', doraise=True)" && echo "$script OK" || echo "$script FAILED"
done
```
**Red flags**: missing files, syntax errors, wrong path references in cron job configs

### 3. Data Directory Health
```bash
# Check what dates have data
ls ~/writing-data/raw/        # Raw data
ls ~/writing-data/charts/     # Generated charts
ls ~/writing-data/drafts/     # Generated articles
ls ~/writing-data/published-html/  # Published HTML
```
**Red flags**: gaps between raw and charts, drafts without matching raw data, newest date missing

### 4. Output Quality (spot check latest)
```bash
# Check draft article has image references
head -5 ~/writing-data/drafts/$(date +%F)*.md
grep -c '!\[.*\](charts/' ~/writing-data/drafts/$(date +%F)*.md
```
**Red flags**: 0 chart references, wrong title format, missing sections

### 5. End-to-End Dry Run
```bash
# Run one day's pipeline manually
python3 .hermes/profiles/writing-domain/skills/a-share-data-collector/scripts/collect_data.py --date $(date +%F)
python3 .hermes/profiles/writing-domain/skills/a-share-review-writer/scripts/generate_charts.py --date $(date +%F)
python3 .hermes/profiles/writing-domain/skills/a-share-review-writer/scripts/generate_review.py --date $(date +%F)
python3 .hermes/profiles/writing-domain/skills/a-share-publisher/scripts/publish_draft.py --validate --date $(date +%F)
```
**Red flags**: any script exits non-zero, missing data warnings, API failures

## Output Format

Present results as:
```
=== Cron Status ===
[ok/warning/error per job]

=== Script Integrity ===
[ok/fail per script]

=== Data Health ===
raw: [dates present], charts: [dates present], drafts: [files]

=== Problem Summary ===
P0: [blocking issues]
P1: [degraded functionality]
P2: [cosmetic/minor]
```

DO NOT start fixing until the user has seen this summary and confirmed direction.

## Comprehensive Fix Workflow (multi-bug sessions)

When the audit finds multiple bugs across scripts, or previous sessions have been
incrementally fixing one bug at a time ("越修越乱"):

1. **List all bugs in one pass** — read every script, find every issue. Do not fix yet.
2. **Group by root cause pattern** — look for the same class of bug across files:
   - None/empty return not checked before subscript
   - Loop breaks on first iteration instead of iterating all
   - Hardcoded paths that differ from cron config paths
3. **Fix all bugs at once** — patch every script in one session. Same-class bugs fixed
   with the same pattern applied consistently.
4. **Clear stale test data** — remove partial outputs from previous broken runs.
5. **End-to-end dry run** — run the full pipeline with a known-good date. Verify
   every stage produces correct output before declaring "fixed".
6. **Clean up test data** — remove dry-run artifacts, leave the pipeline clean for
   the next real trading day.

## Known Bug Patterns

### Pattern 1: Non-trading-day None → subscript crash
**Scripts affected**: collect_data.py (main block)
**Root cause**: `collect_market_data()` returns `None` on non-trading days.
The `if __name__ == "__main__"` block accesses `data['date']` without
checking if `data is None`.
**Fix**: Add `if data is None: sys.exit(0)` before data access.
**Detection**: Any script whose main function can return None must check
for None before subscripting.

### Pattern 2: Loop breaks after first iteration
**Scripts affected**: weekly_summary.py (generate_weekly_charts)
**Root cause**: `generate_weekly_charts()` iterates backward through dates,
finds the first date with data, tries to generate charts — and `break`s
immediately regardless of success or failure. If the first date's chart
generation fails, no other dates are attempted.
**Fix**: Remove the `break` statement. Continue iterating until a date
succeeds or all dates have been tried.
**Detection**: Search for `break` inside loops that call subprocess/network
operations — if the break is unconditional (not inside a success branch),
it's a bug.
