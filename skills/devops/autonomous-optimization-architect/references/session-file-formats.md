# Hermes Session File Formats

All session files live in `~/.hermes/sessions/`. Three file types exist, each with a different structure. Scripts in this skill must handle all three correctly.

## 1. session_*.json — Session Archives (most numerous: ~480 files)

**Purpose**: Full conversation log for a Hermes agent session. Written at session end.

**Structure**:
```json
{
  "session_id": "20260426_114826_04449b",
  "model": "deepseek-v4-pro",
  "base_url": "https://api.deepseek.com",
  "platform": "deepseek",
  "session_start": "2026-04-26T11:48:26",
  "last_updated": "2026-04-26T12:10:00",
  "system_prompt": "...",
  "tools": [...],
  "message_count": 345,
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "...", "finish_reason": "stop"},
    {"role": "tool", "content": "..."}
  ]
}
```

**Key paths for extraction**:
- Model: `data["model"]` (top-level string)
- Provider: `data["platform"]` (top-level string)
- Domain: heuristic from `data["messages"][*]["content"]` text
- Timestamp: `data["session_start"]`
- Token usage: **NONE** — session archives store no per-request token data
- Error detection: `data.get("error_type")`, `data.get("error_message")`, or `"finish_reason"` in messages (only "error"/"length"/"max_tokens" are genuine failures)

## 2. request_dump_*.json — API Request/Response Dumps (~47 files)

**Purpose**: Captures individual API calls — both successful responses and errors. Written per-request by Hermes gateway.

**Structure** (error case — most common in current env):
```json
{
  "timestamp": "2026-04-28T08:02:07.056641",
  "session_id": "cron_b60f3c86dd1b_20260428_080201",
  "reason": "non_retryable_client_error",
  "request": {
    "method": "POST",
    "url": "https://api.deepseek.com/v1/chat/completions",
    "headers": {
      "Authorization": "Bearer ***"
    },
    "body": {
      "model": "deepseek-chat",
      "messages": [...],
      "tools": [...]
    }
  },
  "error": {
    "type": "authentication_error",
    "status_code": 401,
    "message": "Error code: 401 ...",
    "body": {
      "message": "Authentication Fails...",
      "type": "authentication_error",
      "code": "invalid_request_error"
    }
  }
}
```

**Structure** (hypothetical success case — when API key works):
```json
{
  "timestamp": "2026-04-28T...",
  "session_id": "...",
  "reason": null,
  "request": {
    "method": "POST",
    "url": "...",
    "body": { "model": "deepseek-v4-pro", "messages": [...], "tools": [...] }
  },
  "response": {
    "id": "chatcmpl-...",
    "model": "deepseek-v4-pro",
    "usage": {
      "prompt_tokens": 1500,
      "completion_tokens": 320,
      "total_tokens": 1820
    }
  }
}
```

**Key paths for extraction**:
- Model: `data["request"]["body"]["model"]` (nested under request.body)
- Reason/failure: `data["reason"]` — values: "non_retryable_client_error", "max_retries_exhausted", "error", "timeout", or absent/null for success
- Error type: `data["error"]["type"]` (string like "authentication_error", "APIConnectionError", "rate_limit_error")
- HTTP status: `data["error"]["status_code"]` — 401, 429, 500, 502, 503 indicate genuine API failures
- Token usage: `data["response"]["usage"]["prompt_tokens"]` + `["completion_tokens"]` — ONLY present on successful requests
- Timestamp: `data["timestamp"]` (ISO format)

## 3. *.jsonl — Session Transcripts (least numerous: ~9 files)

**Purpose**: Line-by-line streaming transcript of an active session. Each line is a JSON object.

**Structure**:
```
{"role": "session_meta", "model": "deepseek-v4-pro", "platform": "deepseek", "timestamp": "...", "tools": [...]}
{"role": "user", "content": "Hello", "timestamp": "..."}
{"role": "assistant", "content": "Hi!", "finish_reason": "stop", "timestamp": "..."}
{"role": "tool", "content": "{...}", "tool_call_id": "call_...", "timestamp": "..."}
```

**Key paths for extraction**:
- Model: find line with `role == "session_meta"`, read `data["model"]`
- Failures: look for assistant lines with `data["finish_reason"]` in ("error", "tool_calls_error", "length", "max_tokens")
- Timestamp: `data["timestamp"]` on any message (prefer earliest)
- Token usage: **NONE** — transcripts don't store token counts

## Critical Pitfall: No Token Usage Data in Hermes (by design)

Hermes gateway writes `request_dump_*.json` ONLY for failed API requests (auth errors, rate limits, timeouts, exhausted retries). Successful requests do NOT produce a dump file. This is gateway-level design — not a bug, not "API keys broken."

The 480 `session_*.json` archives and 9 `*.jsonl` transcripts also store no per-request token counts.

**Result**: `cost-tracker.py` will always show $0.00 cost from request_dump files. Model/domain counts are accurate — cost estimates rely on session count × model pricing, which gives directional correctness (flash vs pro = 10× price difference) but not exact numbers.

**Workaround paths** (not implemented, for reference):
1. Enable gateway debug logging to capture usage on every request
2. Add a post-session hook that writes a lightweight `{model, tokens}` JSON
3. Accept ~$0.00 in cost-tracker output and use it for model distribution analysis only

## Pitfalls for Script Authors

- **Never use `"error" in content` (string grep) for error detection.** It matches error strings in user messages, tool responses like `{"error": "Subagent timed out..."}`, and delegate_task results. Always parse JSON and check structured fields.
- **Don't assume all `.json` files have the same structure.** session_*.json and request_dump_*.json have completely different schemas. Use filename patterns (`fpath.name.startswith("request_dump_")`) to distinguish them.
- **`data.get("request", {}).get("model")` fails silently** on request_dump files because model is nested deeper: `data["request"]["body"]["model"]`.
