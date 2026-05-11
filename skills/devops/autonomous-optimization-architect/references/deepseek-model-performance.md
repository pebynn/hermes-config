# DeepSeek Model Performance Characteristics

Diagnosis date: 2026-05-01. Source: hermes-agent source code analysis.
Context: why deepseek-v4-pro is 4-5x slower than flash for script writing.

## Root Cause: v4-pro is a native reasoning model

Unlike other DeepSeek models, `deepseek-v4-pro` **always engages thinking mode**
regardless of `reasoning_effort` configuration. The model generates extensive
internal CoT (Chain of Thought) tokens before streaming any visible output.

### Server-side model mapping (from model_metadata.py:173-175)

| Alias               | Maps to                     | Thinking |
|---------------------|-----------------------------|----------|
| `deepseek-chat`     | v4-flash non-thinking mode  | No       |
| `deepseek-reasoner` | v4-flash thinking mode      | Yes      |
| `deepseek-v4-pro`   | (native, auto-thinking)     | **Always** |
| `deepseek-v4-flash` | (native, switchable)        | Optional |

### Three-layer slowdown breakdown

1. **Thinking tokens (~60%)** — v4-pro plans/analyzes/designs before writing code.
   Hidden CoT tokens add latency before output starts. For script tasks, the
   thinking phase can be 2-3x the output length.

2. **Raw generation speed (~25%)** — pro model token/s is inherently slower:
   - v4-pro: $2.80/$8.40 per M in/out (quality-optimized)
   - v4-flash: $0.28/$1.10 per M in/out (throughput-optimized)

3. **Context overhead (~15%)** — 50+ skills, 10 MCP servers, 7000+ char memory
   are processed with full attention on v4-pro (1M context window).

### Key source code evidence

- `run_agent.py:8657` — `_needs_deepseek_tool_reasoning()` returns True for
  ALL deepseek providers, requiring `reasoning_content` on every tool-call turn.
- `chat_completions.py:282-310` — Kimi/TokenHub get explicit `reasoning_effort`
  as top-level param; DeepSeek does NOT. The model controls thinking server-side.
- `hermes_constants.py:144` — `parse_reasoning_effort("medium")` produces
  `{"enabled": True, "effort": "medium"}` but this has NO effect on v4-pro.

### Reasoning effort config DOES NOT disable v4-pro thinking

```yaml
agent:
  reasoning_effort: none  # ← v4-pro IGNORES this; still thinks
```

This parameter is only effective for:
- OpenRouter (controls `reasoning.effort` in extra_body)
- Kimi (controls `reasoning_effort` top-level)
- TokenHub (controls `reasoning_effort` top-level)
- LM Studio (controls `reasoning_effort` top-level)

## Recommended Model Selection Strategy

| Task Type            | Recommended Model   | Why                          |
|----------------------|---------------------|------------------------------|
| Script writing       | deepseek-v4-flash   | No thinking overhead, fast   |
| Data processing      | deepseek-v4-flash   | Throughput-optimized         |
| Batch operations     | deepseek-v4-flash   | Cost-effective at scale      |
| Code review          | deepseek-v4-flash   | Pattern matching, fast       |
| Analysis/Strategy    | deepseek-v4-pro     | Reasoning quality matters    |
| Architecture design  | deepseek-v4-pro     | Needs deep planning          |
| Research synthesis   | deepseek-v4-pro     | Multi-step reasoning         |
| Debugging complex    | deepseek-v4-pro     | Root cause analysis          |

## Quick Switch Commands

```bash
# Switch main model to flash (instant, no restart needed for next /new)
hermes config set model.default deepseek-v4-flash

# Switch delegation model (already flash by default in this config)
hermes config set delegation.model deepseek-v4-flash

# Verify
hermes config | grep -A2 "model:"
```

## Cost Model (for cost-tracker.py)

Update `MODEL_COST_MAP` in `scripts/cost-tracker.py`:

```python
MODEL_COST_MAP = {
    "deepseek-v4-pro":   {"input": 2.80, "output": 8.40},
    "deepseek-v4-flash": {"input": 0.28, "output": 1.10},
    "deepseek-chat":     {"input": 0.27, "output": 1.10},
}
```

> Note: cost-tracker.py in the skill may have outdated pricing ($2.80 vs actual $0.27 for pro input). Verify against https://api-docs.deepseek.com/quick_start/pricing before relying on cost reports.
