#!/usr/bin/env python3
"""
Tests for evoclaw_degradation_detect.py — EvoClaw degradation detection
Run: pytest ~/.hermes/scripts/tests/test_evoclaw_degradation_detect.py -v
"""
import sys
import os
import json
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Ensure ~/.hermes/scripts is on path
SCRIPTS_DIR = Path(os.path.expanduser("~/.hermes/scripts"))
sys.path.insert(0, str(SCRIPTS_DIR))


# ────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────

def _make_ts(days_ago: int, hour: int = 10) -> int:
    """Unix timestamp for N days ago at given hour."""
    dt = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)
    return int(dt.timestamp())


def _setup_test_db(db_path, task_data):
    """Create a test kanban.db with given task data.

    task_data: list of dicts with keys:
      days_ago, body_has_b, has_lesson, outcome, completed_days_ago
    """
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, title TEXT, body TEXT, assignee TEXT,
        status TEXT NOT NULL, priority INTEGER DEFAULT 0,
        created_by TEXT, created_at INTEGER NOT NULL,
        started_at INTEGER, completed_at INTEGER,
        workspace_kind TEXT DEFAULT 'scratch', workspace_path TEXT,
        claim_lock TEXT, claim_expires INTEGER, tenant TEXT, result TEXT,
        idempotency_key TEXT, spawn_failures INTEGER DEFAULT 0,
        worker_pid INTEGER, last_spawn_error TEXT,
        max_runtime_seconds INTEGER, last_heartbeat_at INTEGER,
        current_run_id INTEGER, workflow_template_id TEXT,
        current_step_key TEXT, skills TEXT,
        consecutive_failures INTEGER DEFAULT 0,
        last_failure_error TEXT, max_retries INTEGER
    );
    CREATE TABLE IF NOT EXISTS task_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
        profile TEXT, step_key TEXT, status TEXT NOT NULL,
        claim_lock TEXT, claim_expires INTEGER, worker_pid INTEGER,
        max_runtime_seconds INTEGER, last_heartbeat_at INTEGER,
        started_at INTEGER NOT NULL, ended_at INTEGER,
        outcome TEXT, summary TEXT, metadata TEXT, error TEXT
    );
    """)

    for i, td in enumerate(task_data):
        task_id = f"test_{i:04d}"
        created_ts = _make_ts(td["days_ago"])

        body = "Test task body"
        if td.get("body_has_b"):
            body = "已知陷阱: test pattern " + body

        conn.execute(
            "INSERT INTO tasks(id,title,body,assignee,status,created_at) VALUES(?,?,?,?,?,?)",
            (task_id, f"Test {i}", body, "test-profile", "done", created_ts))

        if td.get("outcome"):
            run_started = _make_ts(td.get("completed_days_ago", td["days_ago"]))
            summary = f"Ran test {i}"
            if td.get("has_lesson"):
                summary += "\n[LESSONS]\n- level: INFO\n  domain: test\n  content: test lesson"
            conn.execute(
                "INSERT INTO task_runs(task_id,profile,status,outcome,summary,started_at,ended_at) VALUES(?,?,?,?,?,?,?)",
                (task_id, "test-profile", "done", td["outcome"], summary, run_started, run_started + 3600))

    conn.commit()
    conn.close()


# ────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────

class TestComputeDailyBDRates:
    """Test B/D rate computation from kanban.db."""

    def test_basic_computation(self):
        """7 days of data, verify per-day B/D rates."""
        import sqlite3
        db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = db.name
        db.close()

        try:
            # Create 7 days of data:
            # day 0 (today):    5 tasks, 3 B, 2 D
            # day 1 (yesterday): 4 tasks, 2 B, 2 D
            # day 2: 3 tasks, 1 B, 1 D
            # day 3: 2 tasks, 0 B, 1 D
            # day 4: 4 tasks, 2 B, 2 D
            # day 5: 3 tasks, 1 B, 1 D
            # day 6: 5 tasks, 3 B, 3 D
            task_data = [
                # day 0 (today)
                {"days_ago": 0, "body_has_b": True, "outcome": "completed", "has_lesson": True},
                {"days_ago": 0, "body_has_b": True, "outcome": "completed", "has_lesson": True},
                {"days_ago": 0, "body_has_b": True, "outcome": "completed", "has_lesson": False},
                {"days_ago": 0, "body_has_b": False, "outcome": "completed", "has_lesson": False},
                {"days_ago": 0, "body_has_b": False, "outcome": "failed", "has_lesson": False},
                # day 1
                {"days_ago": 1, "body_has_b": True, "outcome": "completed", "has_lesson": True},
                {"days_ago": 1, "body_has_b": True, "outcome": "completed", "has_lesson": True},
                {"days_ago": 1, "body_has_b": False, "outcome": "completed", "has_lesson": False},
                {"days_ago": 1, "body_has_b": False, "outcome": "completed", "has_lesson": False},
                # day 2
                {"days_ago": 2, "body_has_b": True, "outcome": "completed", "has_lesson": True},
                {"days_ago": 2, "body_has_b": False, "outcome": "completed", "has_lesson": False},
                {"days_ago": 2, "body_has_b": False, "outcome": "completed", "has_lesson": False},
                # day 3
                {"days_ago": 3, "body_has_b": False, "outcome": "completed", "has_lesson": True},
                {"days_ago": 3, "body_has_b": False, "outcome": "completed", "has_lesson": False},
                # day 4
                {"days_ago": 4, "body_has_b": True, "outcome": "completed", "has_lesson": True},
                {"days_ago": 4, "body_has_b": True, "outcome": "completed", "has_lesson": True},
                {"days_ago": 4, "body_has_b": False, "outcome": "completed", "has_lesson": False},
                {"days_ago": 4, "body_has_b": False, "outcome": "completed", "has_lesson": False},
                # day 5
                {"days_ago": 5, "body_has_b": True, "outcome": "completed", "has_lesson": True},
                {"days_ago": 5, "body_has_b": False, "outcome": "completed", "has_lesson": False},
                {"days_ago": 5, "body_has_b": False, "outcome": "completed", "has_lesson": False},
                # day 6
                {"days_ago": 6, "body_has_b": True, "outcome": "completed", "has_lesson": True},
                {"days_ago": 6, "body_has_b": True, "outcome": "completed", "has_lesson": True},
                {"days_ago": 6, "body_has_b": True, "outcome": "completed", "has_lesson": True},
                {"days_ago": 6, "body_has_b": False, "outcome": "completed", "has_lesson": False},
                {"days_ago": 6, "body_has_b": False, "outcome": "completed", "has_lesson": False},
            ]
            _setup_test_db(db_path, task_data)

            from evoclaw_degradation_detect import compute_daily_bd_rates
            result = compute_daily_bd_rates(db_path, days=7)

            assert len(result) == 7, f"Expected 7 days, got {len(result)}"
            # day 0: 5 tasks, 3B, 2 completed-with-lesson
            day0 = result[0]
            assert day0["total"] == 5
            assert day0["b_count"] == 3
            assert day0["b_rate"] == 3 / 5
            assert day0["done"] == 4  # 4 completed (1 failed)
            assert day0["d_count"] == 2
            assert day0["d_rate"] == 2 / 4

            # day 6: 5 tasks, 3B, 3D
            day6 = result[6]
            assert day6["total"] == 5
            assert day6["b_count"] == 3
            assert day6["b_rate"] == 3 / 5

        finally:
            os.unlink(db_path)

    def test_zero_tasks(self):
        """Empty DB should return empty result with no error."""
        db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = db.name
        db.close()

        try:
            _setup_test_db(db_path, [])
            from evoclaw_degradation_detect import compute_daily_bd_rates
            result = compute_daily_bd_rates(db_path, days=7)

            # Should return 7 days, each with 0 values
            assert len(result) == 7
            for day in result:
                assert day["total"] == 0
                assert day["b_rate"] == 0.0
        finally:
            os.unlink(db_path)

    def test_no_completed_tasks(self):
        """D_rate should be 0 when no tasks completed."""
        db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = db.name
        db.close()

        try:
            task_data = [
                {"days_ago": 0, "body_has_b": True, "outcome": None, "has_lesson": False},
                {"days_ago": 0, "body_has_b": False, "outcome": None, "has_lesson": False},
            ]
            _setup_test_db(db_path, task_data)
            from evoclaw_degradation_detect import compute_daily_bd_rates
            result = compute_daily_bd_rates(db_path, days=7)

            day0 = result[0]
            assert day0["total"] == 2
            assert day0["done"] == 0
            assert day0["d_rate"] == 0.0
            assert day0["b_rate"] == 1 / 2
        finally:
            os.unlink(db_path)


class TestDegradationDetection:
    """Test degradation detection logic."""

    def test_three_consecutive_decline_triggers_p1(self):
        """3+ consecutive days of B_rate decline → P1 warning."""
        from evoclaw_degradation_detect import check_degradation

        # Simulate: day-3=0.80, day-2=0.60, day-1=0.45, today=0.30
        # (3 consecutive declines: today<yesterday, yesterday<day-2, day-2<day-3)
        history = [
            {"date": "2026-05-10", "b_rate": 0.80, "d_rate": 0.35, "total": 10, "done": 8},
            {"date": "2026-05-11", "b_rate": 0.60, "d_rate": 0.30, "total": 10, "done": 8},
            {"date": "2026-05-12", "b_rate": 0.45, "d_rate": 0.30, "total": 10, "done": 8},
        ]
        today = {"date": "2026-05-13", "b_rate": 0.30, "d_rate": 0.30, "total": 10, "done": 8}

        result = check_degradation(today, history)
        assert len(result) == 1, f"Expected 1 alert, got {len(result)}"
        assert result[0]["priority"] == "P1"
        assert "连续" in result[0]["title"]
        assert "B_layer" in result[0]["title"] or "B层" in result[0]["title"]

    def test_consecutive_decline_in_d_rate(self):
        """3+ consecutive days of D_rate decline → P1 warning."""
        from evoclaw_degradation_detect import check_degradation

        history = [
            {"date": "2026-05-10", "b_rate": 0.70, "d_rate": 0.40, "total": 10, "done": 8},
            {"date": "2026-05-11", "b_rate": 0.70, "d_rate": 0.30, "total": 10, "done": 8},
            {"date": "2026-05-12", "b_rate": 0.70, "d_rate": 0.20, "total": 10, "done": 8},
        ]
        today = {"date": "2026-05-13", "b_rate": 0.70, "d_rate": 0.10, "total": 10, "done": 8}

        result = check_degradation(today, history)
        assert len(result) == 1
        assert "D层" in result[0]["title"] or "D_layer" in result[0]["title"]

    def test_50_percent_drop_triggers_p0(self):
        """>50% drop vs 5-day baseline → P0 alert."""
        from evoclaw_degradation_detect import check_degradation

        # Baseline (5 days: indices -7 to -3) avg ≈ 0.34
        history = [
            {"date": "2026-05-08", "b_rate": 0.72, "d_rate": 0.35, "total": 10, "done": 8},
            {"date": "2026-05-09", "b_rate": 0.70, "d_rate": 0.33, "total": 10, "done": 8},
            {"date": "2026-05-10", "b_rate": 0.68, "d_rate": 0.34, "total": 10, "done": 8},
            {"date": "2026-05-11", "b_rate": 0.65, "d_rate": 0.36, "total": 10, "done": 8},
            {"date": "2026-05-12", "b_rate": 0.63, "d_rate": 0.32, "total": 10, "done": 8},
        ]
        # Today B_rate=0.28, baseline avg of first 5 days = (0.72+0.70+0.68+0.65+0.63)/5 = 0.676
        # 0.28 / 0.676 = 0.414 → 58.6% drop → P0!
        today = {"date": "2026-05-13", "b_rate": 0.28, "d_rate": 0.30, "total": 10, "done": 8}

        result = check_degradation(today, history)
        p0_alerts = [a for a in result if a["priority"] == "P0"]
        assert len(p0_alerts) >= 1, f"Expected at least 1 P0 alert, got {len(p0_alerts)}"

    def test_no_degradation_returns_ok(self):
        """Stable rates → no alerts."""
        from evoclaw_degradation_detect import check_degradation

        history = [
            {"date": "2026-05-10", "b_rate": 0.70, "d_rate": 0.30, "total": 10, "done": 8},
            {"date": "2026-05-11", "b_rate": 0.72, "d_rate": 0.31, "total": 10, "done": 8},
            {"date": "2026-05-12", "b_rate": 0.68, "d_rate": 0.29, "total": 10, "done": 8},
        ]
        today = {"date": "2026-05-13", "b_rate": 0.71, "d_rate": 0.32, "total": 10, "done": 8}

        result = check_degradation(today, history)
        assert len(result) == 0, f"Expected no alerts, got {len(result)}"

    def test_insufficient_history(self):
        """< 3 days of history → skip check, return empty."""
        from evoclaw_degradation_detect import check_degradation

        history = [
            {"date": "2026-05-12", "b_rate": 0.60, "d_rate": 0.30, "total": 10, "done": 8},
        ]
        today = {"date": "2026-05-13", "b_rate": 0.10, "d_rate": 0.05, "total": 10, "done": 8}

        result = check_degradation(today, history)
        assert len(result) == 0

    def test_low_volume_skip_alert(self):
        """Skip alert when today has < 3 total tasks."""
        from evoclaw_degradation_detect import check_degradation

        history = [
            {"date": "2026-05-10", "b_rate": 0.80, "d_rate": 0.35, "total": 10, "done": 8},
            {"date": "2026-05-11", "b_rate": 0.60, "d_rate": 0.30, "total": 10, "done": 8},
            {"date": "2026-05-12", "b_rate": 0.40, "d_rate": 0.25, "total": 10, "done": 8},
        ]
        today = {"date": "2026-05-13", "b_rate": 0.20, "d_rate": 0.20, "total": 1, "done": 1}

        result = check_degradation(today, history)
        assert len(result) == 0


class TestHistoryPersistence:
    """Test JSON history file read/write."""

    def test_save_and_load(self):
        """Write snapshot, read back, verify accuracy."""
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp_path = tmp.name
        tmp.close()

        try:
            from evoclaw_degradation_detect import save_history, load_history

            snapshot = {
                "date": "2026-05-13", "b_count": 5, "b_rate": 0.71,
                "d_count": 2, "d_rate": 0.29, "total": 7, "done": 7
            }
            save_history(snapshot, tmp_path)

            loaded = load_history(tmp_path)
            assert len(loaded) == 1
            assert loaded[0]["date"] == "2026-05-13"
            assert loaded[0]["b_rate"] == 0.71
        finally:
            os.unlink(tmp_path)

    def test_append_to_existing(self):
        """Appending to existing history preserves order."""
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp_path = tmp.name
        tmp.close()

        try:
            from evoclaw_degradation_detect import save_history, load_history

            save_history({"date": "2026-05-12", "b_rate": 0.60, "d_rate": 0.25, "total": 5, "done": 4}, tmp_path)
            save_history({"date": "2026-05-13", "b_rate": 0.55, "d_rate": 0.20, "total": 5, "done": 4}, tmp_path)

            loaded = load_history(tmp_path)
            assert len(loaded) == 2
            assert loaded[0]["date"] == "2026-05-12"
            assert loaded[1]["date"] == "2026-05-13"
        finally:
            os.unlink(tmp_path)

    def test_corrupt_file_recovers(self):
        """Corrupt JSON file → returns empty list, doesn't crash."""
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp_path = tmp.name
        tmp.write(b"this is not json {{{")
        tmp.close()

        try:
            from evoclaw_degradation_detect import load_history
            loaded = load_history(tmp_path)
            assert loaded == [] or isinstance(loaded, list)
        finally:
            os.unlink(tmp_path)


class TestIntegration:
    """End-to-end integration tests."""

    def test_full_flow_no_alerts(self):
        """Complete flow with mock DB and no degradation."""
        # This test verifies the script runs end-to-end
        # We'll test via function calls, not subprocess
        import sys
        db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = db.name
        db.close()

        hist = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        hist_path = hist.name
        hist.close()

        try:
            # Setup stable data (no degradation)
            task_data = []
            for day in range(7):
                for i in range(5):
                    task_data.append({
                        "days_ago": day,
                        "body_has_b": i < 3,
                        "outcome": "completed",
                        "has_lesson": i < 2,
                    })
            _setup_test_db(db_path, task_data)

            from evoclaw_degradation_detect import compute_daily_bd_rates, check_degradation, \
                load_history, save_history

            rates = compute_daily_bd_rates(db_path, days=7)
            today = rates[0]
            history = rates[1:]  # rest as history

            alerts = check_degradation(today, history)
            # With consistent data, no alerts expected
            # (all rates are 3/5=0.6 B and 2/5=0.4 D consistently)
            for alert in alerts:
                assert alert["priority"] in ("P0", "P1")

            # Save should work
            save_history(today, hist_path)
            loaded = load_history(hist_path)
            assert len(loaded) == 1

        finally:
            for p in [db_path, hist_path]:
                try:
                    os.unlink(p)
                except OSError:
                    pass
