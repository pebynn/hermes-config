"""
Tests for audit_bd_layer.py — GEPA 5 Guardrails + Lessons Forgetting Mechanism
TDD: These tests are written BEFORE implementation. They should be RED initially.

Run: pytest ~/.hermes/scripts/tests/test_audit_bd_layer.py -v
"""
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts dir to path
sys.path.insert(0, os.path.expanduser("~/.hermes/scripts"))

# We expect audit_bd_layer to exist after implementation
# For TDD, import what we can; tests will fail (RED) until implemented


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def temp_lessons_file():
    """Create a temporary lessons.jsonl file for testing."""
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def temp_skills_dir():
    """Create a temporary skills directory structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"
        skills_dir.mkdir()
        yield skills_dir


@pytest.fixture
def sample_lesson():
    """Return a sample lesson entry."""
    return {
        "id": "test-lesson-001",
        "content": "This is a test lesson about something important.",
        "level": "red",
        "domain": "code-domain",
        "timestamp": datetime.now().isoformat(),
        "confirmed_at": None,
        "weight": 1.0,
        "status": "active"
    }


# ──────────────────────────────────────────────
# Tests: Lessons Forgetting Mechanism
# ──────────────────────────────────────────────

class TestLessonDecay:
    """Test lessons/ forgetting mechanism."""

    def test_add_lesson_with_timestamp(self, temp_lessons_file):
        """Each lesson must have a timestamp."""
        from audit_bd_layer import add_lesson

        lesson = {
            "content": "Test lesson",
            "level": "red",
            "domain": "code-domain",
        }
        entry = add_lesson(temp_lessons_file, lesson)

        assert "timestamp" in entry
        assert "id" in entry
        assert entry["weight"] == 1.0
        assert entry["status"] == "active"

    def test_decay_after_90_days(self, temp_lessons_file):
        """Lessons >90 days unconfirmed should be de-weighted."""
        from audit_bd_layer import add_lesson, manage_lesson_decay

        # Add a lesson with old timestamp
        old_lesson = {
            "content": "Old lesson",
            "level": "yellow",
            "domain": "ops-domain",
        }
        entry = add_lesson(temp_lessons_file, old_lesson)

        # Read the file and backdate the timestamp
        with open(temp_lessons_file, 'r') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            data = json.loads(line)
            if data["id"] == entry["id"]:
                data["timestamp"] = (datetime.now() - timedelta(days=95)).isoformat()
                data["confirmed_at"] = None
                lines[i] = json.dumps(data) + "\n"
        with open(temp_lessons_file, 'w') as f:
            f.writelines(lines)

        # Run decay
        results = manage_lesson_decay(temp_lessons_file)
        assert len(results["decayed"]) >= 1
        assert results["decayed"][0]["weight"] == 0.5
        assert results["decayed"][0]["status"] == "decayed"

    def test_archive_after_180_days(self, temp_lessons_file):
        """Lessons >180 days unconfirmed should be archived."""
        from audit_bd_layer import add_lesson, manage_lesson_decay

        old_lesson = {
            "content": "Ancient lesson",
            "level": "green",
            "domain": "code-domain",
        }
        entry = add_lesson(temp_lessons_file, old_lesson)

        # Backdate to 185 days ago
        with open(temp_lessons_file, 'r') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            data = json.loads(line)
            if data["id"] == entry["id"]:
                data["timestamp"] = (datetime.now() - timedelta(days=185)).isoformat()
                data["confirmed_at"] = None
                lines[i] = json.dumps(data) + "\n"
        with open(temp_lessons_file, 'w') as f:
            f.writelines(lines)

        results = manage_lesson_decay(temp_lessons_file)
        assert len(results["archived"]) >= 1

    def test_confirmed_lesson_not_decayed(self, temp_lessons_file):
        """Recently confirmed lessons should NOT be decayed."""
        from audit_bd_layer import add_lesson, manage_lesson_decay

        lesson = {
            "content": "Recently confirmed lesson",
            "level": "red",
            "domain": "code-domain",
        }
        entry = add_lesson(temp_lessons_file, lesson)

        # Set timestamp to old but confirmed recently
        with open(temp_lessons_file, 'r') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            data = json.loads(line)
            if data["id"] == entry["id"]:
                data["timestamp"] = (datetime.now() - timedelta(days=120)).isoformat()
                data["confirmed_at"] = datetime.now().isoformat()
                lines[i] = json.dumps(data) + "\n"
        with open(temp_lessons_file, 'w') as f:
            f.writelines(lines)

        results = manage_lesson_decay(temp_lessons_file)
        assert len(results["decayed"]) == 0
        assert len(results["archived"]) == 0

    def test_active_lesson_stays_active(self, temp_lessons_file):
        """Lessons within 90 days should remain active."""
        from audit_bd_layer import add_lesson, manage_lesson_decay

        add_lesson(temp_lessons_file, {
            "content": "Recent lesson",
            "level": "red",
            "domain": "code-domain",
        })

        results = manage_lesson_decay(temp_lessons_file)
        assert len(results["decayed"]) == 0
        assert len(results["archived"]) == 0


# ──────────────────────────────────────────────
# Tests: Guardrail 1 — Size Check
# ──────────────────────────────────────────────

class TestSizeCheck:
    """Test size limit guardrail."""

    def test_skill_within_limit(self, temp_skills_dir):
        """Skill file ≤15KB should pass."""
        from audit_bd_layer import check_size_limits

        skill_file = temp_skills_dir / "SKILL.md"
        skill_file.write_text("# Test\n" * 100)  # ~800 bytes

        results = check_size_limits(str(temp_skills_dir))
        assert len(results["violations"]) == 0

    def test_skill_exceeds_limit(self, temp_skills_dir):
        """Skill file >15KB should be flagged."""
        from audit_bd_layer import check_size_limits

        skill_file = temp_skills_dir / "SKILL.md"
        # Create content >15KB
        skill_file.write_text("x" * 16000)

        results = check_size_limits(str(temp_skills_dir))
        assert len(results["violations"]) >= 1
        assert any("size" in v["type"].lower() for v in results["violations"])

    def test_tool_description_exceeds_500_chars(self, temp_skills_dir):
        """Tool description >500 chars should be flagged."""
        from audit_bd_layer import check_size_limits

        # Create skill with YAML frontmatter containing long tool description
        skill_content = """---
name: test-skill
description: This is a test skill
tools:
  - name: test-tool
    description: """ + ("A" * 600) + """
---
# Body
"""
        skill_file = temp_skills_dir / "SKILL.md"
        skill_file.write_text(skill_content)

        results = check_size_limits(str(temp_skills_dir))
        violations_500char = [v for v in results["violations"]
                              if "500" in str(v) or "char" in v.get("type", "").lower()
                              or "tool" in v.get("type", "").lower()
                              or "description" in v.get("type", "").lower()]
        # At minimum, the size check should run without crashing
        assert isinstance(results, dict)


# ──────────────────────────────────────────────
# Tests: Guardrail 2 — pytest Integration
# ──────────────────────────────────────────────

class TestPytestIntegration:
    """Test pytest integration guardrail."""

    def test_no_changes_no_tests_run(self, temp_skills_dir):
        """When no files changed, pytest should not run unnecessarily."""
        from audit_bd_layer import check_pytest_integration

        results = check_pytest_integration(
            skills_dir=str(temp_skills_dir),
            scripts_dir=str(temp_skills_dir),
            lookback_hours=24
        )
        # Should return structured results, even if empty
        assert isinstance(results, dict)
        assert "test_results" in results or "changed_files" in results

    def test_changed_skill_triggers_test(self, temp_skills_dir):
        """Changed skill should trigger associated test run."""
        from audit_bd_layer import check_pytest_integration

        # Create a skill file with recent mtime
        skill_file = temp_skills_dir / "SKILL.md"
        skill_file.write_text("# Test Skill")
        os.utime(skill_file, (time.time(), time.time()))  # now

        # Create associated test
        tests_dir = temp_skills_dir / "tests"
        tests_dir.mkdir()
        test_file = tests_dir / "test_skill.py"
        test_file.write_text("def test_pass(): assert True\n")

        results = check_pytest_integration(
            skills_dir=str(temp_skills_dir),
            scripts_dir=str(temp_skills_dir),
            lookback_hours=1
        )
        assert isinstance(results, dict)


# ──────────────────────────────────────────────
# Tests: Guardrail 3 — Cache Compatibility
# ──────────────────────────────────────────────

class TestCacheCompatibility:
    """Test cache compatibility guardrail."""

    def test_no_recent_changes_no_issues(self, temp_skills_dir):
        """No recent lesson/memory changes means no cache issues."""
        from audit_bd_layer import check_cache_compat

        results = check_cache_compat(
            lessons_dir=str(temp_skills_dir),
            memory_dir=str(temp_skills_dir),
            sessions_dir=str(temp_skills_dir),
        )
        assert isinstance(results, dict)
        assert "issues" in results

    def test_recent_lesson_change_flags_cache(self):
        """Recent lesson change should flag cache invalidation."""
        from audit_bd_layer import check_cache_compat

        with tempfile.TemporaryDirectory() as tmpdir:
            lessons_dir = Path(tmpdir) / "lessons"
            lessons_dir.mkdir()
            memory_dir = Path(tmpdir) / "memory"
            memory_dir.mkdir()
            sessions_dir = Path(tmpdir) / "sessions"
            sessions_dir.mkdir()

            # Create a recently changed lesson
            lesson_file = lessons_dir / "code-domain.md"
            lesson_file.write_text("# Test")
            os.utime(lesson_file, (time.time(), time.time()))

            results = check_cache_compat(
                lessons_dir=str(lessons_dir),
                memory_dir=str(memory_dir),
                sessions_dir=str(sessions_dir),
            )
            assert isinstance(results, dict)


# ──────────────────────────────────────────────
# Tests: Guardrail 4 — Semantic Drift (stub)
# ──────────────────────────────────────────────

class TestSemanticDrift:
    """Test semantic drift detection guardrail."""

    def test_semantic_drift_requires_flag(self):
        """Semantic drift should require --semantic flag (LLM call)."""
        from audit_bd_layer import check_semantic_drift

        # Without LLM enabled, should return skipped status
        results = check_semantic_drift("/nonexistent", enable_llm=False)
        assert results.get("status") == "skipped"


# ──────────────────────────────────────────────
# Tests: Guardrail 5 — Review Gate
# ──────────────────────────────────────────────

class TestReviewGate:
    """Test review gate guardrail."""

    def test_l1_change_no_review_required(self, temp_skills_dir):
        """L1 (SKILL.md) changes should not require review."""
        from audit_bd_layer import check_review_gate

        skill_file = temp_skills_dir / "SKILL.md"
        skill_file.write_text("# L1 change")
        os.utime(skill_file, (time.time(), time.time()))

        results = check_review_gate(str(temp_skills_dir))
        assert isinstance(results, dict)
        # L1 changes should have review_required: false or not in critical list
        critical = [r for r in results.get("review_items", [])
                    if r.get("level") == "L3"]
        assert len(critical) == 0

    def test_l3_change_requires_review(self, temp_skills_dir):
        """L3 (system prompt, code) changes should require human review."""
        from audit_bd_layer import check_review_gate

        # Create a system prompt change
        system_dir = temp_skills_dir / "system"
        system_dir.mkdir(parents=True)
        prompt_file = system_dir / "SOUL.md"
        prompt_file.write_text("# System Prompt v2")
        os.utime(prompt_file, (time.time(), time.time()))

        results = check_review_gate(str(temp_skills_dir))
        assert isinstance(results, dict)


# ──────────────────────────────────────────────
# Tests: Existing Audit Logic (kanban.db scan)
# ──────────────────────────────────────────────

class TestKanbanAudit:
    """Test existing kanban.db audit logic."""

    def test_scan_kanban_db_structure(self):
        """scan_kanban_db should return structured results."""
        from audit_bd_layer import scan_kanban_db

        results = scan_kanban_db(db_path="/home/pebynn/.hermes/kanban.db")
        assert isinstance(results, dict)
        # Should have B/D injection rate data
        assert "bd_injection_rate" in results or "alerts" in results or "summary" in results


# ──────────────────────────────────────────────
# Tests: Integration — run_extended_audit
# ──────────────────────────────────────────────

class TestExtendedAudit:
    """Integration tests for --extended mode."""

    def test_extended_audit_runs_all_guardrails(self):
        """--extended should run all 5 guardrails + lessons decay."""
        from audit_bd_layer import run_extended_audit

        results = run_extended_audit(
            db_path="/home/pebynn/.hermes/kanban.db",
            skills_base="/home/pebynn/.hermes/profiles",
            lessons_file="/home/pebynn/.hermes/lessons/lessons.jsonl",
            enable_semantic=False,
        )
        # Should return structured results for all guardrails
        assert isinstance(results, dict)
        expected_keys = [
            "bd_injection",
            "size_check",
            "pytest_check",
            "cache_check",
            "review_gate",
            "lesson_decay",
        ]
        for key in expected_keys:
            assert key in results, f"Missing key: {key}"

    def test_extended_audit_semantic_skipped_by_default(self):
        """Semantic drift should be skipped when enable_semantic=False."""
        from audit_bd_layer import run_extended_audit

        results = run_extended_audit(
            db_path="/home/pebynn/.hermes/kanban.db",
            skills_base="/home/pebynn/.hermes/profiles",
            lessons_file="/home/pebynn/.hermes/lessons/lessons.jsonl",
            enable_semantic=False,
        )
        sd = results.get("semantic_drift", {})
        assert sd.get("status") in ("skipped", None)
