"""Quick integration test — parse real README."""
import sys
sys.path.insert(0, "/home/pebynn/.hermes/kanban/workspaces/t_c197c415")

from quarterly_hermes_ecosystem_scan import parse_entries, diff_entries, generate_report

# README was saved from curl earlier — reuse it
text = open("/home/pebynn/.hermes/kanban/workspaces/t_c197c415/test_readme.md", "r").read()
entries = parse_entries(text)
print(f"Parsed {len(entries)} entries from README")
for e in entries[:5]:
    print(f"  [{e['maturity']}] {e['name']} — {e.get('description','')[:80]}")
print(f"  ... and {len(entries)-5} more")

# Verify diff works
new, removed = diff_entries(entries[:5], entries[3:8])
print(f"\nDiff test: {len(new)} new, {len(removed)} removed (expected 3 new, 3 removed)")

# Verify report
report = generate_report(new, removed, "2026-01-01")
print(f"\nReport generated: {len(report)} chars")
print(report[:500])
