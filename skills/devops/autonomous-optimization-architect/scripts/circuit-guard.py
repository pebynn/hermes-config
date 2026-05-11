#!/usr/bin/env python3
"""
circuit-guard.py — Hermes circuit breaker and cost guard for
autonomous-optimization-architect.

Reads Hermes config.yaml, checks model costs against configured limits,
detects repeated failure patterns from session logs, and can auto-patch
config.yaml to switch to fallback models when the circuit is broken.

Usage:
  python3 circuit-guard.py                          # check status (JSON output)
  python3 circuit-guard.py --auto-fix               # auto-patch config on warnings
  python3 circuit-guard.py --config /path/to/config.yaml
  python3 circuit-guard.py --sessions-dir ~/.hermes/sessions
  python3 circuit-guard.py --thresholds /path/to/cost-thresholds.yaml
  python3 circuit-guard.py --verbose
"""

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_COST_THRESHOLDS = {
    "per_session_max": 0.50,
    "per_day_max": 5.00,
    "per_domain_daily": {
        "research": 3.00,
        "code": 2.00,
        "ec": 1.00,
        "finance": 1.00,
    },
    "circuit_breaker": {
        "consecutive_failures": 5,
        "window_minutes": 30,
    },
    "alert_channels": ["terminal", "cron-report"],
}

DEFAULT_MODEL_COSTS = {
    "deepseek-v4-pro":   {"input": 2.80, "output": 8.40},
    "deepseek-v4-flash": {"input": 0.28, "output": 1.10},
    "deepseek-chat":     {"input": 0.27, "output": 1.10},
}

# Paths
HERMES_CONFIG = os.path.expanduser("~/.hermes/config.yaml")
HERMES_SESSIONS = os.path.expanduser("~/.hermes/sessions")
COST_THRESHOLDS_PATH = os.path.expanduser(
    "~/.hermes/skills/devops/autonomous-optimization-architect/references/cost-thresholds.yaml"
)

# ---------------------------------------------------------------------------
# YAML helpers (stdlib-only — works without PyYAML)
# ---------------------------------------------------------------------------

def _parse_yaml(text: str) -> dict:
    """Minimal YAML parser for our config format (nested keys, scalars, lists)."""
    result: dict = {}
    # Handle simple flat key: value
    lines = text.splitlines()
    indent_stack: list[dict] = [result]
    prev_indent = 0

    for line in lines:
        if not line.strip() or line.strip().startswith("#"):
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        while indent < prev_indent and len(indent_stack) > 1:
            indent_stack.pop()
            prev_indent -= 2  # assume 2-space indent

        # key: value or key:
        m = re.match(r"^([\w-]+):\s*(.*?)$", stripped)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        current = indent_stack[-1]

        if val == "":
            # Nested dict
            new_dict: dict = {}
            current[key] = new_dict
            indent_stack.append(new_dict)
        elif val.startswith("[") and val.endswith("]"):
            # List
            items = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",")]
            current[key] = [v for v in items if v]
        else:
            # Scalar — try numeric
            current[key] = _parse_scalar(val)

        prev_indent = indent

    return result


def _parse_scalar(val: str) -> Any:
    """Parse a YAML scalar value."""
    if val.lower() in ("true", "yes", "on"):
        return True
    if val.lower() in ("false", "no", "off"):
        return False
    if val.lower() == "null":
        return None
    try:
        if "." in val:
            return float(val)
        return int(val)
    except (ValueError, TypeError):
        return val.strip('"').strip("'")


def _read_yaml_file(path: str) -> dict:
    """Read a YAML file, trying PyYAML first, then falling back to manual parsing."""
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        return {}
    try:
        import yaml  # type: ignore[import-untyped]
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        with open(path, "r") as f:
            return _parse_yaml(f.read())


def _write_yaml_file(path: str, data: dict) -> None:
    """Write a dict as YAML, preferring PyYAML if available."""
    path = os.path.expanduser(path)
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    try:
        import yaml
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    except ImportError:
        # Manual YAML serialization for simple dicts
        lines = _serialize_yaml(data)
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")


def _serialize_yaml(data: dict, indent: int = 0) -> list[str]:
    """Serialize a simple dict to YAML lines."""
    lines: list[str] = []
    prefix = " " * indent
    for key, val in data.items():
        if isinstance(val, dict):
            lines.append(f"{prefix}{key}:")
            lines.extend(_serialize_yaml(val, indent + 2))
        elif isinstance(val, list):
            lines.append(f"{prefix}{key}:")
            for item in val:
                lines.append(f"{prefix}  - {item}")
        elif isinstance(val, bool):
            lines.append(f"{prefix}{key}: {'true' if val else 'false'}")
        elif val is None:
            lines.append(f"{prefix}{key}: null")
        elif isinstance(val, (int, float)):
            lines.append(f"{prefix}{key}: {val}")
        else:
            lines.append(f"{prefix}{key}: {val}")
    return lines


def _parse_json(path: Path) -> dict | None:
    """Read and parse a JSON file, returning None on failure."""
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError, PermissionError):
        return None


# ---------------------------------------------------------------------------
# Config reading
# ---------------------------------------------------------------------------

def read_hermes_config(path: str | None = None) -> dict:
    """Read Hermes config.yaml into a dict."""
    config_path = path or HERMES_CONFIG
    return _read_yaml_file(config_path)


def read_thresholds(path: str | None = None) -> dict:
    """Read cost threshold config, falling back to defaults."""
    if path and os.path.isfile(os.path.expanduser(path)):
        return _read_yaml_file(path)
    if os.path.isfile(COST_THRESHOLDS_PATH):
        return _read_yaml_file(COST_THRESHOLDS_PATH)
    return dict(DEFAULT_COST_THRESHOLDS)  # return a copy


# ---------------------------------------------------------------------------
# Session analysis
# ---------------------------------------------------------------------------

def scan_sessions(sessions_dir: str, window_minutes: int = 30) -> dict:
    """Scan recent session logs for genuine model/API failures.

    Uses structured JSON parsing to avoid false positives from:
      - delegate_task responses with "error": "Subagent timed out..."
      - Tool responses with "error" field in normal JSON output
      - Error strings in user/assistant conversation text

    Recognises genuine failures via:
      - request_dump_*.json: reason=non_retryable_client_error|max_retries_exhausted
      - request_dump_*.json: error.status_code in (429, 500, 502, 503)
      - session_*.json: error_type / error_message fields in session metadata
      - *.jsonl: assistant finish_reason = error / tool_calls_error / length / max_tokens

    Returns:
        dict with fail_count, cost_24h, and a list of recent errors
    """
    sdir = Path(os.path.expanduser(sessions_dir))
    if not sdir.is_dir():
        return {"fail_count": 0, "cost_24h": 0.0, "errors": [], "total_sessions": 0}

    now = datetime.now(timezone.utc)
    window_ago = now - timedelta(minutes=window_minutes)

    recent_failures = 0
    recent_cost = 0.0
    total_sessions = 0
    errors: list[str] = []

    # HTTP status codes that indicate genuine API/model failures
    FAILURE_HTTP_STATUSES = {429, 500, 502, 503}

    for fpath in sorted(sdir.iterdir(), reverse=True):
        if not fpath.is_file():
            continue
        if not (fpath.suffix in (".json", ".jsonl") or fpath.name.endswith(".jsonl")):
            continue

        try:
            mtime = datetime.fromtimestamp(fpath.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue

        is_recent_fail_window = mtime >= window_ago
        if not is_recent_fail_window:
            continue  # skip files outside the failure window

        total_sessions += 1
        fname = fpath.name

        # ------------------------------------------------------------------
        # JSONL — look for genuine finish_reason failures in assistant messages
        # ------------------------------------------------------------------
        if fpath.suffix == ".jsonl":
            fail_count_in_file = 0
            for line in _read_jsonl_lines(fpath):
                if line.get("role") == "assistant":
                    fr = line.get("finish_reason", "")
                    if fr in ("error", "tool_calls_error", "length", "max_tokens"):
                        fail_count_in_file += 1

            if fail_count_in_file > 0:
                recent_failures += fail_count_in_file
                errors.append(f"  {fname}: {fail_count_in_file} model failures (finish_reason)")

        # ------------------------------------------------------------------
        # JSON — parse and inspect for genuine failures
        # ------------------------------------------------------------------
        elif fpath.suffix == ".json":
            data = _parse_json(fpath)
            if not data:
                continue

            # --- request_dump_*.json: structured error capture ---
            if fname.startswith("request_dump_"):
                reason = data.get("reason", "")

                # Reason-based failures
                if reason in ("non_retryable_client_error", "max_retries_exhausted", "error", "timeout"):
                    recent_failures += 1

                    err = data.get("error", {})
                    status_code = err.get("status_code") if isinstance(err, dict) else None
                    err_type = err.get("type", reason) if isinstance(err, dict) else reason
                    detail = f"reason={reason}"
                    if status_code:
                        detail += f", status={status_code}"
                    if err_type:
                        detail += f", type={err_type}"
                    errors.append(f"  {fname}: {detail}")

                # HTTP status-code-based failures
                err = data.get("error", {})
                if isinstance(err, dict):
                    sc = err.get("status_code")
                    if sc and sc in FAILURE_HTTP_STATUSES:
                        # Only count if not already counted by reason above
                        if reason not in ("non_retryable_client_error", "max_retries_exhausted", "error", "timeout"):
                            recent_failures += 1
                            errors.append(f"  {fname}: HTTP {sc}")

            # --- session_*.json: look for error_type / error_message metadata ---
            elif fname.startswith("session_"):
                # Check top-level error fields
                err_type = data.get("error_type", "")
                err_msg = data.get("error_message", "")

                # Check messages for error markers
                messages = data.get("messages", [])
                for msg in messages:
                    if isinstance(msg, dict):
                        fr = msg.get("finish_reason", "")
                        if fr in ("error", "tool_calls_error", "length", "max_tokens"):
                            recent_failures += 1
                            errors.append(f"  {fname}: finish_reason={fr}")
                            break  # count once per session

    return {
        "fail_count": recent_failures,
        "cost_24h": round(recent_cost, 4),
        "errors": errors[:20],  # cap at 20 entries
        "total_sessions": total_sessions,
    }


def _read_jsonl_lines(path: Path) -> list[dict]:
    """Parse a JSONL file into a list of dicts, skipping unparseable lines."""
    results: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except (OSError, PermissionError):
        pass
    return results


# ---------------------------------------------------------------------------
# Circuit breaker logic
# ---------------------------------------------------------------------------

def circuit_check(
    config: dict,
    thresholds: dict,
    verbose: bool = False,
) -> dict:
    """Evaluate circuit breaker status based on config and session analysis.

    Returns status dict with: status, active_model, suggestion, fail_count, cost_24h
    """
    cb_config = thresholds.get("circuit_breaker", DEFAULT_COST_THRESHOLDS["circuit_breaker"])
    max_fails = cb_config.get("consecutive_failures", 5)
    window_min = cb_config.get("window_minutes", 30)

    # Determine active model
    active_model = config.get("model", {})
    if isinstance(active_model, dict):
        active_model = active_model.get("default", "unknown")
    if isinstance(active_model, str) and not active_model:
        active_model = "unknown"

    # Scan recent sessions
    session_data = scan_sessions(HERMES_SESSIONS, window_minutes=window_min)
    fail_count = session_data["fail_count"]

    status = "ok"
    suggestion = ""

    if fail_count >= max_fails:
        status = "circuit_broken"
        suggestion = (
            f"Circuit broken: {fail_count} failures in {window_min}min window. "
            f"Suggest switching from '{active_model}' to a fallback model "
            f"(e.g., deepseek-v4-flash or deepseek-chat)."
        )
    elif fail_count >= max_fails * 0.6:
        status = "warning"
        suggestion = (
            f"Warning: {fail_count}/{max_fails} failure threshold approaching. "
            f"Monitor '{active_model}' closely."
        )

    if verbose:
        print(f"Circuit check: {fail_count} fails in {window_min}min window (threshold: {max_fails})")
        if session_data["errors"]:
            print("Recent errors:")
            for e in session_data["errors"]:
                print(f"  {e}")

    return {
        "status": status,
        "active_model": active_model,
        "suggestion": suggestion,
        "fail_count": fail_count,
        "fail_threshold": max_fails,
        "window_minutes": window_min,
        "cost_24h": session_data["cost_24h"],
        "total_sessions": session_data["total_sessions"],
    }


# ---------------------------------------------------------------------------
# Auto-fix logic
# ---------------------------------------------------------------------------

def auto_fix_config(config_path: str, status: dict, verbose: bool = False) -> bool:
    """Auto-patch config.yaml to switch to fallback model.

    Creates a backup of the original config first.

    Returns True if changes were made.
    """
    config_path = os.path.expanduser(config_path)
    if not os.path.isfile(config_path):
        print(f"error: config not found: {config_path}", file=sys.stderr)
        return False

    # Backup
    backup_path = config_path + f".bak.{int(time.time())}"
    shutil.copy2(config_path, backup_path)
    if verbose:
        print(f"Backup saved to {backup_path}")

    # Read current config
    config = read_hermes_config(config_path)

    # Determine fallback
    current_model = status.get("active_model", "unknown")
    fallback_map = {
        "deepseek-v4-pro": "deepseek-v4-flash",
        "deepseek-reasoner": "deepseek-v4-flash",
        "deepseek-v3": "deepseek-chat",
    }
    fallback = fallback_map.get(current_model, "deepseek-chat")

    # Update model block
    if "model" not in config:
        config["model"] = {}
    if isinstance(config["model"], dict):
        config["model"]["default"] = fallback

    # Also update delegation model if present
    if "delegation" in config and isinstance(config["delegation"], dict):
        config["delegation"]["model"] = fallback

    # Write updated config
    _write_yaml_file(config_path, config)

    if verbose:
        print(f"Config updated: model.default changed from '{current_model}' to '{fallback}'")
        print(f"Run `hermes config reload` or restart Hermes to apply changes.")

    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hermes circuit breaker and cost guard — detect model failures and auto-fallback."
    )
    parser.add_argument(
        "--config", default=HERMES_CONFIG,
        help=f"Path to Hermes config.yaml (default: {HERMES_CONFIG})",
    )
    parser.add_argument(
        "--sessions-dir", default=HERMES_SESSIONS,
        help=f"Path to sessions directory (default: {HERMES_SESSIONS})",
    )
    parser.add_argument(
        "--thresholds", default=None,
        help="Path to cost-thresholds.yaml (default: skill references/cost-thresholds.yaml)",
    )
    parser.add_argument(
        "--auto-fix", action="store_true",
        help="Auto-patch config.yaml to fallback model if circuit is broken",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print detailed error information",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON instead of human-readable text (suppresses --verbose text)",
    )
    args = parser.parse_args()

    config = read_hermes_config(args.config)
    thresholds = read_thresholds(args.thresholds)

    status = circuit_check(config, thresholds, verbose=(args.verbose and not args.json))

    if args.auto_fix and status["status"] in ("warning", "circuit_broken"):
        changed = auto_fix_config(args.config, status, verbose=(args.verbose and not args.json))
        if changed:
            status["config_patched"] = True
            status["fallback_model"] = config.get("model", {}).get("default", "unknown") if isinstance(config.get("model"), dict) else "unknown"

    if args.json:
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        status_icon = {"ok": "OK", "warning": "WARNING", "circuit_broken": "CIRCUIT BROKEN"}
        icon = status_icon.get(status["status"], "UNKNOWN")
        print(f"Hermes Circuit Guard — Status: {icon}")
        print(f"  Active model:   {status['active_model']}")
        print(f"  Fail count:     {status['fail_count']} / {status['fail_threshold']} (threshold)")
        print(f"  Window:         {status['window_minutes']} min")
        print(f"  Total sessions: {status['total_sessions']}")
        if status["cost_24h"] > 0:
            print(f"  Cost (24h):     ${status['cost_24h']:.4f}")
        if status.get("config_patched"):
            print(f"  Config patched: yes → fallback '{status.get('fallback_model', 'unknown')}'")
        if status.get("suggestion"):
            print(f"\n  Suggestion: {status['suggestion']}")
        if args.verbose and status.get("fail_count", 0) > 0:
            print("\n  Recent errors:")
            for e in status.get("errors", []):
                print(f"    {e}")


if __name__ == "__main__":
    main()
