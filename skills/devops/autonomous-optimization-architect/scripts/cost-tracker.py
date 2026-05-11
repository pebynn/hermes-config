#!/usr/bin/env python3
"""
cost-tracker.py — Hermes session cost tracking for autonomous-optimization-architect.

Parses ~/.hermes/sessions/*.json and *.jsonl files,
extracts model/provider info, estimates LLM API costs,
and groups results by day/model/domain.

Cost rates (per million tokens):
  deepseek-v4-pro:   $2.80 input,   $8.40 output
  deepseek-v4-flash: $0.28 input,   $1.10 output
  deepseek-reasoner: $2.80 input,   $8.40 output
  deepseek-chat:     $0.27 input,   $1.10 output
  default (unknown): $1.00 input,   $4.00 output

Usage:
  python3 cost-tracker.py                          # full report (last 7 days)
  python3 cost-tracker.py --days 30                # last 30 days
  python3 cost-tracker.py --model deepseek-v4-pro  # filter by model
  python3 cost-tracker.py --domain code            # filter by domain
  python3 cost-tracker.py --threshold 0.50         # flag sessions over $0.50
  python3 cost-tracker.py --json                   # JSON output
  python3 cost-tracker.py --sessions-dir ~/.hermes/sessions
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Cost model — $ per million tokens (updated 2026-05-10)
#
# DeepSeek pricing has two components for input:
#   cache_miss — full price for new/uncached tokens
#   cache_hit  — ~1/10 price for tokens already in context cache
# Output tokens always at full price.
#
# V4 Pro discounted rates valid until 2026-05-31 (75% off base).
# After expiry, cache_miss reverts to ~$1.74, output to ~$3.48.
# Cache-hit stays at 1/10 of cache-miss permanently.
#
# Sources: DeepSeek official pricing page, tokenmix.ai, openai-hub.com
# ---------------------------------------------------------------------------
MODEL_COST_MAP = {
    # V4 Pro — 75% discount active until 2026-05-31
    "deepseek-v4-pro":     {"cache_miss": 0.435, "cache_hit": 0.003625, "output": 0.87},
    # V4 Flash — standard pricing (no temp discount)
    "deepseek-v4-flash":   {"cache_miss": 0.14,  "cache_hit": 0.0028,   "output": 0.28},
    # V3.2 / deepseek-chat — standard pricing
    "deepseek-chat":       {"cache_miss": 0.28,  "cache_hit": 0.028,    "output": 0.42},
    "deepseek-v3":         {"cache_miss": 0.27,  "cache_hit": 0.027,    "output": 1.10},
    # Reasoner uses same base as V3.2 (legacy)
    "deepseek-reasoner":   {"cache_miss": 0.28,  "cache_hit": 0.028,    "output": 0.42},
    # Non-DeepSeek models (no cache differentiation)
    "gpt-4o":              {"cache_miss": 2.50, "cache_hit": 2.50, "output": 10.00},
    "gpt-4o-mini":         {"cache_miss": 0.15, "cache_hit": 0.15, "output": 0.60},
    "claude-sonnet-4":     {"cache_miss": 3.00, "cache_hit": 3.00, "output": 15.00},
    "claude-haiku-3.5":    {"cache_miss": 0.80, "cache_hit": 0.80, "output": 4.00},
}

# Default cache hit rate for DeepSeek models (validated by user: 80-90%)
DEFAULT_CACHE_HIT_RATE = 0.85

DEFAULT_COST = {"cache_miss": 1.00, "cache_hit": 1.00, "output": 4.00}

# Domain detection keywords
DOMAIN_KEYWORDS: list[tuple[str, list[str]]] = [
    ("research", ["research", "arxiv", "paper", "literature", "academic", "study"]),
    ("code",     ["code", "python", "javascript", "bug", "commit", "pr ", "pull request",
                   "refactor", "test", "debug", "function", "class", "api"]),
    ("ec",       ["ec-", "ecommerce", "电商", "pdd", "拼多多", "fulfillment",
                   "supply", "inventory", "order"]),
    ("finance",  ["finance", "stock", "quant", "trade", "portfolio", "market",
                   "investment", " A股", "factor"]),
]

# Token estimation fallback (calibrated against DeepSeek billing: 8x real/estimate ratio)
# 350/150 was too low — each "message" triggers full context (system prompt + history)
MSG_INPUT_TOKENS = 2800
MSG_OUTPUT_TOKENS = 1200

# Pattern to match JSONL session_meta lines
RE_SESSION_META = re.compile(
    r'\"role\"\s*:\s*\"session_meta\"\s*.*?\"model\"\s*:\s*\"([^\"]+)\"'
)

RE_USAGE = re.compile(
    r'"usage"\s*:\s*\{[^}]*?"input_tokens"\s*:\s*(\d+)[^}]*?"output_tokens"\s*:\s*(\d+)[^}]*?\}',
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file returning all parseable JSON objects."""
    docs: list[dict] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    docs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except (OSError, PermissionError):
        pass
    return docs


def _parse_json(path: Path) -> dict | None:
    """Read a JSON file."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        return json.loads(raw)
    except (OSError, json.JSONDecodeError, PermissionError):
        return None


def _detect_model_and_provider(docs: list[dict]) -> tuple[str, str]:
    """Extract model/provider from session metadata."""
    for d in docs:
        if d.get("role") == "session_meta":
            model = d.get("model", "") or ""
            platform = d.get("platform", "") or ""
            return model, platform
    return "unknown", "unknown"


def _detect_domain(sessions_text: str) -> str:
    """Heuristic domain detection by scanning session content."""
    text_lower = sessions_text.lower()
    scores: dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS:
        for kw in keywords:
            if kw.lower() in text_lower:
                scores[domain] = scores.get(domain, 0) + 1
    if not scores:
        return "general"
    return max(scores, key=scores.get)  # type: ignore[arg-type]


def _estimate_cost(model: str, input_tokens: int, output_tokens: int, cache_hit_rate: float = None) -> float:
    """Estimate cost in USD based on token counts, model, and cache hit rate.

    For DeepSeek models: splits input into cache-hit (at ~1/10 price) and cache-miss.
    For non-DeepSeek models: cache_hit = cache_miss (no differentiation).
    
    cache_hit_rate defaults to DEFAULT_CACHE_HIT_RATE (0.85) for DeepSeek models,
    0.0 for others (no cache benefit).
    """
    rates = MODEL_COST_MAP.get(model, DEFAULT_COST)
    
    # Detect DeepSeek models for cache-hit awareness
    is_deepseek = "deepseek" in model.lower()
    if cache_hit_rate is None:
        cache_hit_rate = DEFAULT_CACHE_HIT_RATE if is_deepseek else 0.0
    
    cache_hit_tokens = int(input_tokens * cache_hit_rate)
    cache_miss_tokens = input_tokens - cache_hit_tokens
    
    input_cost = (
        cache_miss_tokens / 1_000_000 * rates["cache_miss"] +
        cache_hit_tokens / 1_000_000 * rates["cache_hit"]
    )
    output_cost = output_tokens / 1_000_000 * rates["output"]
    
    return input_cost + output_cost


def _parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse various timestamp formats to datetime."""
    if not ts_str:
        return None
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y%m%d_%H%M%S",
    ]:
        try:
            return datetime.strptime(ts_str[:26], fmt).replace(tzinfo=timezone.utc)
        except (ValueError, IndexError):
            continue
    return None


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

class SessionRecord:
    def __init__(self) -> None:
        self.path = ""
        self.model = "unknown"
        self.provider = "unknown"
        self.domain = "general"
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost = 0.0
        self.timestamp: datetime | None = None
        self.failures = 0  # count of error responses
        self.source = "unknown"  # "interactive", "cron", or "request_dump"

    @property
    def day_key(self) -> str:
        if self.timestamp:
            return self.timestamp.strftime("%Y-%m-%d")
        return "unknown"

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "model": self.model,
            "provider": self.provider,
            "domain": self.domain,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost": round(self.cost, 6),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "failures": self.failures,
            "source": self.source,
        }


def analyze_sessions(sessions_dir: str, days: int = 7) -> list[SessionRecord]:
    """Walk session files and extract cost records.

    Handles three file types:
      - session_*.json       — Hermes session archives (model at top level, no usage tokens)
      - request_dump_*.json  — API request dumps (model in request.body, usage in response.usage if successful)
      - *.jsonl              — Session transcripts (model in session_meta, no usage tokens)
    """
    sdir = Path(sessions_dir).expanduser().resolve()
    if not sdir.is_dir():
        print(f"error: sessions directory not found: {sdir}", file=sys.stderr)
        sys.exit(1)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    records: list[SessionRecord] = []

    for fpath in sorted(sdir.iterdir()):
        if not fpath.is_file():
            continue
        if not (fpath.suffix in (".json", ".jsonl") or fpath.name.endswith(".jsonl")):
            continue

        # Determine file modification time as fallback timestamp
        try:
            mtime = datetime.fromtimestamp(fpath.stat().st_mtime, tz=timezone.utc)
        except OSError:
            mtime = datetime.now(timezone.utc)

        rec = SessionRecord()
        rec.path = str(fpath)

        # ------------------------------------------------------------------
        # JSONL — session transcripts
        # ------------------------------------------------------------------
        if fpath.suffix == ".jsonl":
            docs = _parse_jsonl(fpath)
            if not docs:
                continue
            rec.model, rec.provider = _detect_model_and_provider(docs)

            # Collect all text for domain detection
            all_text = " ".join(
                str(d.get("content", "")) for d in docs
                if d.get("role") in ("user", "assistant")
            )
            rec.domain = _detect_domain(all_text)

            # Count failures from assistant finish_reason
            for d in docs:
                if d.get("role") == "assistant" and d.get("finish_reason") in (
                    "error", "tool_calls_error", "max_tokens",
                ):
                    rec.failures += 1

            # Try to get timestamp from first user message or meta
            for d in docs:
                ts = _parse_timestamp(d.get("timestamp"))
                if ts:
                    rec.timestamp = ts
                    break
            if rec.timestamp is None:
                rec.timestamp = mtime

            # Mark as cron session + estimate tokens from message count
            rec.source = "cron"
            msg_count = sum(1 for d in docs if d.get("role") in ("user", "assistant"))
            if msg_count > 0 and rec.input_tokens == 0 and rec.output_tokens == 0:
                rec.input_tokens = msg_count * MSG_INPUT_TOKENS
                rec.output_tokens = msg_count * MSG_OUTPUT_TOKENS

        # ------------------------------------------------------------------
        # JSON — two sub-types
        # ------------------------------------------------------------------
        elif fpath.suffix == ".json":
            data = _parse_json(fpath)
            if not data:
                continue

            is_request_dump = fpath.name.startswith("request_dump_")

            if is_request_dump:
                # request_dump_*.json — API request/response capture
                rec.source = "request_dump"
                rec.model = (
                    data.get("request", {})
                    .get("body", {})
                    .get("model", "unknown")
                )
                rec.provider = data.get("request", {}).get("provider", "unknown")

                # Usage data lives in response.usage (prompt_tokens / completion_tokens)
                usage = data.get("response", {}).get("usage", {})
                if isinstance(usage, dict) and usage:
                    rec.input_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
                    rec.output_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
                    rec.cost = _estimate_cost(rec.model, rec.input_tokens, rec.output_tokens)

                # Failure detection
                reason = data.get("reason", "")
                if reason in ("max_retries_exhausted", "non_retryable_client_error", "error", "timeout"):
                    rec.failures += 1

                # Domain from request text
                req_text = json.dumps(data.get("request", {}))
                rec.domain = _detect_domain(req_text)

                # Timestamp
                ts = _parse_timestamp(data.get("timestamp"))
                rec.timestamp = ts or mtime

            else:
                # session_*.json — Hermes session archives
                rec.source = "interactive"
                rec.model = data.get("model", "unknown")
                rec.provider = data.get("platform", "unknown")

                # Session archives store no per-request token usage;
                # usage data exists only in request_dump files
                # FALLBACK: estimate from message_count (rough but better than $0.00)
                msg_count = data.get("message_count", 0)
                if msg_count > 0:
                    rec.input_tokens = msg_count * MSG_INPUT_TOKENS
                    rec.output_tokens = msg_count * MSG_OUTPUT_TOKENS
                    rec.cost = _estimate_cost(rec.model, rec.input_tokens, rec.output_tokens)
                else:
                    rec.input_tokens = 0
                    rec.output_tokens = 0
                    rec.cost = 0.0

                # Detect domain from messages content
                messages = data.get("messages", [])
                all_text = " ".join(
                    str(m.get("content", "")) for m in messages
                    if m.get("role") in ("user", "assistant")
                )
                rec.domain = _detect_domain(all_text)

                # Timestamp from session_start
                ts = _parse_timestamp(data.get("session_start"))
                rec.timestamp = ts or mtime

        # Filter by date
        if rec.timestamp and rec.timestamp < cutoff:
            continue

        # Calculate cost if not already set (JSONL paths without usage)
        if rec.cost == 0.0 and (rec.input_tokens > 0 or rec.output_tokens > 0):
            rec.cost = _estimate_cost(rec.model, rec.input_tokens, rec.output_tokens)

        records.append(rec)

    return records


def build_report(
    records: list[SessionRecord],
    model_filter: str | None = None,
    domain_filter: str | None = None,
    threshold: float | None = None,
) -> dict:
    """Aggregate records into a structured report."""
    total_cost = 0.0
    total_input = 0
    total_output = 0
    by_model: dict[str, dict] = defaultdict(lambda: {"cost": 0.0, "sessions": 0, "input_tokens": 0, "output_tokens": 0})
    by_domain: dict[str, dict] = defaultdict(lambda: {"cost": 0.0, "sessions": 0})
    by_day: dict[str, dict] = defaultdict(lambda: {"cost": 0.0, "sessions": 0})
    by_source: dict[str, dict] = defaultdict(lambda: {"cost": 0.0, "sessions": 0, "input_tokens": 0, "output_tokens": 0})
    flagged: list[dict] = []

    for rec in records:
        if model_filter and rec.model != model_filter:
            continue
        if domain_filter and rec.domain != domain_filter:
            continue

        total_cost += rec.cost
        total_input += rec.input_tokens
        total_output += rec.output_tokens

        by_model[rec.model]["cost"] += rec.cost
        by_model[rec.model]["sessions"] += 1
        by_model[rec.model]["input_tokens"] += rec.input_tokens
        by_model[rec.model]["output_tokens"] += rec.output_tokens

        by_domain[rec.domain]["cost"] += rec.cost
        by_domain[rec.domain]["sessions"] += 1

        by_day[rec.day_key]["cost"] += rec.cost
        by_day[rec.day_key]["sessions"] += 1

        by_source[rec.source]["cost"] += rec.cost
        by_source[rec.source]["sessions"] += 1
        by_source[rec.source]["input_tokens"] += rec.input_tokens
        by_source[rec.source]["output_tokens"] += rec.output_tokens

        if threshold is not None and rec.cost > threshold:
            flagged.append(rec.to_dict())

    return {
        "period": {
            "total_sessions": len(records),
            "total_cost": round(total_cost, 4),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
        },
        "by_model": dict(by_model),
        "by_domain": dict(by_domain),
        "by_source": dict(by_source),
        "by_day": {
            k: {"cost": round(v["cost"], 4), "sessions": v["sessions"]}
            for k, v in sorted(by_day.items())
        },
        "flagged_sessions": flagged,
    }


def print_report(report: dict) -> None:
    """Pretty-print the cost report."""
    p = report["period"]
    print(f"=== Hermes Cost Report ===")
    print(f"Sessions:  {p['total_sessions']}")
    print(f"Total cost: ${p['total_cost']:.4f}")
    print(f"Input tokens:  {p['total_input_tokens']:,}")
    print(f"Output tokens: {p['total_output_tokens']:,}")
    print()

    print("--- By Model ---")
    for model, data in sorted(report["by_model"].items(), key=lambda x: -x[1]["cost"]):
        avg_cost = data["cost"] / data["sessions"] if data["sessions"] else 0
        print(f"  {model}: ${data['cost']:.4f} ({data['sessions']} sessions, ${avg_cost:.4f}/session)")

    print()
    print("--- By Domain ---")
    for domain, data in sorted(report["by_domain"].items(), key=lambda x: -x[1]["cost"]):
        print(f"  {domain}: ${data['cost']:.4f} ({data['sessions']} sessions)")

    print()
    print("--- By Source ---")
    source_labels = {"interactive": "💬 交互对话", "cron": "⏰ Cron任务", "request_dump": "📡 API原始记录"}
    for source, data in sorted(report["by_source"].items(), key=lambda x: -x[1]["cost"]):
        label = source_labels.get(source, source)
        avg_cost = data["cost"] / data["sessions"] if data["sessions"] else 0
        print(f"  {label}: ${data['cost']:.4f} ({data['sessions']} sessions, ${avg_cost:.4f}/session, {data['input_tokens']:,}+{data['output_tokens']:,} tokens)")

    print()
    print("--- By Day ---")
    for day, data in report["by_day"].items():
        print(f"  {day}: ${data['cost']:.4f} ({data['sessions']} sessions)")

    flagged = report.get("flagged_sessions", [])
    if flagged:
        print()
        print(f"--- Flagged Sessions (exceeded threshold) ---")
        for s in flagged:
            print(f"  {s['path']}: ${s['cost']:.4f} ({s['model']}, {s['domain']})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hermes session cost tracker — analyze LLM API costs from session logs."
    )
    parser.add_argument(
        "--sessions-dir",
        default="~/.hermes/sessions",
        help="Path to Hermes sessions directory (default: ~/.hermes/sessions)",
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="Number of days to look back (default: 7)",
    )
    parser.add_argument(
        "--model", default=None,
        help="Filter results by model name",
    )
    parser.add_argument(
        "--domain", default=None,
        help="Filter results by domain (research|code|ec|finance)",
    )
    parser.add_argument(
        "--threshold", type=float, default=None,
        help="Flag individual sessions exceeding this cost threshold (USD)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON instead of human-readable table",
    )
    args = parser.parse_args()

    records = analyze_sessions(args.sessions_dir, days=args.days)
    report = build_report(
        records,
        model_filter=args.model,
        domain_filter=args.domain,
        threshold=args.threshold,
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
