"""
TDD tests for quarterly_hermes_ecosystem_scan.py
Strategy: test core parse/diff/report logic. Network calls mocked.
"""
import pytest
import json
import sys
import os
from pathlib import Path

# Ensure the script dir is importable
SCRIPT_DIR = Path(os.environ["HERMES_KANBAN_WORKSPACE"])
sys.path.insert(0, str(SCRIPT_DIR))

# We'll import functions after creating the script
# For now, define test fixtures and expected behaviors


class TestParseEntries:
    """RED: parse_entries must extract project info from README bullet lines."""

    SAMPLE_LINES = [
        '- **[beta]** [hermes-plugins](https://github.com/42-evey/hermes-plugins) by [42-evey](https://github.com/42-evey) - Goal management, inter-agent bridge.',
        '- **[production]** [SkillClaw](https://github.com/AMAP-ML/SkillClaw) by [AMAP-ML](https://github.com/AMAP-ML) - Open-source companion that auto-evolves skills.',
        '- **[experimental]** [super-hermes](https://github.com/Cranot/super-hermes) by [Cranot](https://github.com/Cranot) - Teaches Hermes to write its own prompts.',
    ]

    def test_parse_entries_extracts_name_url(self):
        """Each entry must yield (name, url, maturity, author, description)."""
        from quarterly_hermes_ecosystem_scan import parse_entries
        text = "\n".join(self.SAMPLE_LINES)
        entries = parse_entries(text)
        assert len(entries) == 3

        # Check first entry
        e0 = entries[0]
        assert e0["name"] == "hermes-plugins"
        assert e0["url"] == "https://github.com/42-evey/hermes-plugins"
        assert e0["maturity"] == "beta"
        assert e0["author"] == "42-evey"

        # Check second entry
        e1 = entries[1]
        assert e1["name"] == "SkillClaw"
        assert e1["url"] == "https://github.com/AMAP-ML/SkillClaw"
        assert e1["maturity"] == "production"

        # Check third entry
        e2 = entries[2]
        assert e2["name"] == "super-hermes"
        assert e2["maturity"] == "experimental"

    def test_parse_entries_empty_text(self):
        """Empty text returns empty list, no crash."""
        from quarterly_hermes_ecosystem_scan import parse_entries
        assert parse_entries("") == []
        assert parse_entries("Some random text\nwithout bullets\n") == []

    def test_parse_entries_skips_non_entries(self):
        """Lines without the right pattern are ignored."""
        from quarterly_hermes_ecosystem_scan import parse_entries
        text = (
            "# Title\n\n"
            "Some intro paragraph.\n\n"
            "- **[beta]** [valid-project](https://github.com/x/y) by [author](https://github.com/a) - desc\n"
            "- Just a regular bullet\n"
        )
        entries = parse_entries(text)
        assert len(entries) == 1
        assert entries[0]["name"] == "valid-project"

    def test_parse_entries_handles_stars_in_name(self):
        """Some entries have stars count in description, not in name."""
        from quarterly_hermes_ecosystem_scan import parse_entries
        text = '- **[production]** [Hermes Agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com) - The core project. 23k+ stars.'
        entries = parse_entries(text)
        assert len(entries) == 1
        assert entries[0]["name"] == "Hermes Agent"


class TestDiffEntries:
    """RED: diff must detect new, removed, and unchanged."""

    def test_detect_new_entries(self):
        from quarterly_hermes_ecosystem_scan import diff_entries
        current = [
            {"name": "A", "url": "http://a"},
            {"name": "B", "url": "http://b"},
        ]
        last = [
            {"name": "A", "url": "http://a"},
        ]
        new, removed = diff_entries(current, last)
        assert len(new) == 1
        assert new[0]["name"] == "B"
        assert len(removed) == 0

    def test_detect_removed_entries(self):
        from quarterly_hermes_ecosystem_scan import diff_entries
        current = [
            {"name": "A", "url": "http://a"},
        ]
        last = [
            {"name": "A", "url": "http://a"},
            {"name": "B", "url": "http://b"},
        ]
        new, removed = diff_entries(current, last)
        assert len(new) == 0
        assert len(removed) == 1
        assert removed[0]["name"] == "B"

    def test_no_change(self):
        from quarterly_hermes_ecosystem_scan import diff_entries
        entries = [{"name": "A", "url": "http://a"}]
        new, removed = diff_entries(entries, entries)
        assert len(new) == 0
        assert len(removed) == 0

    def test_both_new_and_removed(self):
        from quarterly_hermes_ecosystem_scan import diff_entries
        current = [
            {"name": "A", "url": "http://a"},
            {"name": "C", "url": "http://c"},
        ]
        last = [
            {"name": "A", "url": "http://a"},
            {"name": "B", "url": "http://b"},
        ]
        new, removed = diff_entries(current, last)
        assert len(new) == 1
        assert new[0]["name"] == "C"
        assert len(removed) == 1
        assert removed[0]["name"] == "B"


class TestGenerateReport:
    """RED: report must have proper Markdown format with sections."""

    def test_report_with_new_and_removed(self):
        from quarterly_hermes_ecosystem_scan import generate_report
        new = [
            {"name": "NewProject", "url": "https://github.com/x/new", "maturity": "beta", "author": "x"},
        ]
        removed = [
            {"name": "OldProject", "url": "https://github.com/y/old", "maturity": "production", "author": "y"},
        ]
        report = generate_report(new, removed, "2026-07-01")
        assert "# Awesome Hermes Agent" in report
        assert "2026-07-01" in report
        assert "## 🆕 New Entries" in report
        assert "## ❌ Removed Entries" in report
        assert "NewProject" in report
        assert "https://github.com/x/new" in report
        assert "OldProject" in report
        assert "https://github.com/y/old" in report

    def test_report_only_new(self):
        from quarterly_hermes_ecosystem_scan import generate_report
        new = [{"name": "N", "url": "http://n", "maturity": "beta", "author": "a"}]
        report = generate_report(new, [], "2026-07-01")
        assert "## 🆕 New Entries" in report
        assert "## ❌ Removed Entries" not in report

    def test_report_only_removed(self):
        from quarterly_hermes_ecosystem_scan import generate_report
        removed = [{"name": "R", "url": "http://r", "maturity": "production", "author": "b"}]
        report = generate_report([], removed, "2026-07-01")
        assert "## ❌ Removed Entries" in report
        assert "## 🆕 New Entries" not in report

    def test_report_empty(self):
        """Should return None or empty for no changes (silent exit)."""
        from quarterly_hermes_ecosystem_scan import generate_report
        report = generate_report([], [], "2026-07-01")
        assert report is None or report == ""


class TestSnapshotIO:
    """RED: snapshot load/save must work with JSON round-trip."""

    def test_save_and_load_snapshot(self, tmp_path):
        from quarterly_hermes_ecosystem_scan import save_snapshot, load_snapshot
        entries = [
            {"name": "A", "url": "http://a"},
            {"name": "B", "url": "http://b"},
        ]
        snap_path = tmp_path / "test_snap.json"
        save_snapshot(snap_path, entries)
        assert snap_path.exists()

        loaded = load_snapshot(snap_path)
        assert len(loaded) == 2
        assert loaded[0]["name"] == "A"

    def test_load_nonexistent_snapshot(self, tmp_path):
        from quarterly_hermes_ecosystem_scan import load_snapshot
        snap_path = tmp_path / "nonexistent.json"
        loaded = load_snapshot(snap_path)
        assert loaded == []
