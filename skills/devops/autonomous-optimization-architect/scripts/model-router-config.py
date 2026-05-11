#!/usr/bin/env python3
"""
model-router-config.py — Hermes model routing and failover chain manager
for autonomous-optimization-architect.

Reads/writes Hermes config.yaml to manage delegation model settings,
generates failover chain configurations, and provides cost/performance
analysis for model routing decisions.

Actions:
  show      — display current delegation + model config
  validate  — validate config completeness and detect issues
  suggest   — suggest optimal model routing based on cost/performance

Usage:
  python3 model-router-config.py show
  python3 model-router-config.py show --config /path/to/config.yaml
  python3 model-router-config.py validate
  python3 model-router-config.py suggest
  python3 model-router-config.py suggest --failover-chain /path/to/failover-chain.yaml
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERMES_CONFIG = os.path.expanduser("~/.hermes/config.yaml")
FAILOVER_CHAIN_PATH = os.path.expanduser(
    "~/.hermes/skills/devops/autonomous-optimization-architect/references/failover-chain.yaml"
)
COST_TRACKER_PATH = os.path.expanduser(
    "~/.hermes/skills/devops/autonomous-optimization-architect/scripts/cost-tracker.py"
)

MODEL_META: dict[str, dict[str, Any]] = {
    "deepseek-v4-pro": {
        "provider": "deepseek",
        "cost_per_m_input": 2.80,
        "cost_per_m_output": 8.40,
        "tier": "premium",
        "capabilities": ["reasoning", "coding", "research"],
    },
    "deepseek-v4-flash": {
        "provider": "deepseek",
        "cost_per_m_input": 0.28,
        "cost_per_m_output": 1.10,
        "tier": "standard",
        "capabilities": ["general", "coding", "quick"],
    },
    "deepseek-reasoner": {
        "provider": "deepseek",
        "cost_per_m_input": 2.80,
        "cost_per_m_output": 8.40,
        "tier": "premium",
        "capabilities": ["reasoning", "math", "complex"],
    },
    "deepseek-chat": {
        "provider": "deepseek",
        "cost_per_m_input": 0.27,
        "cost_per_m_output": 1.10,
        "tier": "budget",
        "capabilities": ["general", "chat", "simple"],
    },
}


# ---------------------------------------------------------------------------
# YAML helpers (stdlib fallback)
# ---------------------------------------------------------------------------

def _read_yaml_file(path: str) -> dict:
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        return {}
    try:
        import yaml  # type: ignore[import-untyped]
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        return _parse_yaml(path)


def _write_yaml_file(path: str, data: dict) -> None:
    path = os.path.expanduser(path)
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    try:
        import yaml
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    except ImportError:
        lines = _serialize_yaml(data)
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")


def _serialize_yaml(data: dict, indent: int = 0) -> list[str]:
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


def _parse_yaml(path: str) -> dict:
    raw = Path(os.path.expanduser(path)).read_text(errors="replace")
    return _yaml_parse_text(raw)


def _yaml_parse_text(text: str) -> dict:
    result: dict = {}
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
            prev_indent -= 2

        m = re.match(r"^([\w-]+):\s*(.*?)$", stripped)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        current = indent_stack[-1]

        if val == "":
            new_dict: dict = {}
            current[key] = new_dict
            indent_stack.append(new_dict)
        elif val.startswith("[") and val.endswith("]"):
            items = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",")]
            current[key] = [v for v in items if v]
        else:
            current[key] = _yaml_scalar(val)

        prev_indent = indent
    return result


def _yaml_scalar(val: str) -> Any:
    if val.lower() in ("true", "yes"):
        return True
    if val.lower() in ("false", "no"):
        return False
    if val.lower() == "null":
        return None
    try:
        if "." in val:
            return float(val)
        return int(val)
    except (ValueError, TypeError):
        return val.strip('"').strip("'")


# ---------------------------------------------------------------------------
# Config reading
# ---------------------------------------------------------------------------

def read_config(path: str = HERMES_CONFIG) -> dict:
    return _read_yaml_file(path)


# ---------------------------------------------------------------------------
# Action: show
# ---------------------------------------------------------------------------

def action_show(config: dict) -> dict:
    """Display current model, provider, and delegation configuration."""
    model_section = config.get("model", {})
    if isinstance(model_section, dict):
        default_model = model_section.get("default", "not set")
        default_provider = model_section.get("provider", "not set")
    else:
        default_model = str(model_section) if model_section else "not set"
        default_provider = "not set"

    providers = config.get("providers", {})
    delegation = config.get("delegation", {})
    fallback_providers = config.get("fallback_providers", [])

    # Current model info
    model_info = MODEL_META.get(default_model, {})
    cost_per_m = {
        "input": model_info.get("cost_per_m_input", 0),
        "output": model_info.get("cost_per_m_output", 0),
    }

    return {
        "default_model": default_model,
        "default_provider": default_provider,
        "model_tier": model_info.get("tier", "unknown"),
        "model_capabilities": model_info.get("capabilities", []),
        "cost_per_million_tokens": cost_per_m,
        "providers_configured": list(providers.keys()) if isinstance(providers, dict) else [],
        "delegation": {
            "model": delegation.get("model", "not set"),
            "provider": delegation.get("provider", "not set"),
            "base_url": delegation.get("base_url", "not set"),
            "api_key_set": bool(delegation.get("api_key", "")),
            "max_concurrent_children": delegation.get("max_concurrent_children", 3),
        },
        "fallback_providers": fallback_providers if isinstance(fallback_providers, list) else [],
    }


# ---------------------------------------------------------------------------
# Action: validate
# ---------------------------------------------------------------------------

def action_validate(config: dict) -> dict:
    """Validate configuration completeness and detect issues."""
    issues: list[str] = []
    warnings: list[str] = []

    # Check model section
    model_section = config.get("model", {})
    if not model_section:
        issues.append("Missing 'model' section in config.yaml")
    elif isinstance(model_section, dict):
        if not model_section.get("default"):
            issues.append("model.default is not set")
        if not model_section.get("provider"):
            warnings.append("model.provider is not set (may use env var)")

    # Check providers
    providers = config.get("providers", {})
    if isinstance(providers, dict) and not providers:
        warnings.append("No providers configured in 'providers' section")

    # Check delegation
    delegation = config.get("delegation", {})
    if isinstance(delegation, dict):
        if not delegation.get("api_key") and not os.environ.get("DEEPSEEK_API_KEY"):
            warnings.append("delegation.api_key is not set and no DEEPSEEK_API_KEY env var")
        if not delegation.get("model"):
            warnings.append("delegation.model is not set (will inherit model.default)")
        if delegation.get("max_concurrent_children", 3) < 1:
            issues.append("delegation.max_concurrent_children must be >= 1")

    # Check API key via env var (for main model)
    main_provider = model_section.get("provider", "deepseek") if isinstance(model_section, dict) else "deepseek"
    env_key_name = f"{main_provider.upper()}_API_KEY"
    if not os.environ.get(env_key_name) and not os.environ.get("DEEPSEEK_API_KEY"):
        warnings.append(
            f"No {env_key_name} env var found — provider may not be authenticated"
        )

    status = "ok" if not issues else "error"
    if not issues and warnings:
        status = "warning"

    return {
        "status": status,
        "issues": issues,
        "warnings": warnings,
        "config_complete": len(issues) == 0,
    }


# ---------------------------------------------------------------------------
# Action: suggest
# ---------------------------------------------------------------------------

def action_suggest(
    config: dict,
    failover_chain_path: str | None = None,
) -> dict:
    """Suggest optimal model routing based on cost and config analysis."""
    model_section = config.get("model", {})
    current_model = model_section.get("default", "unknown") if isinstance(model_section, dict) else "unknown"
    current_provider = model_section.get("provider", "unknown") if isinstance(model_section, dict) else "unknown"

    # Read failover chain
    chain = _read_yaml_file(failover_chain_path or FAILOVER_CHAIN_PATH)

    # Build suggestions
    suggestions: list[dict] = []
    chain_result: dict = {}

    if chain:
        primary = chain.get("primary", {})
        fallback = chain.get("fallback", {})
        cost_saving = chain.get("cost_saving", {})
        per_domain = chain.get("per_domain", {})

        chain_result = {
            "primary": primary,
            "fallback": fallback,
            "cost_saving": cost_saving,
            "per_domain_overrides": per_domain if isinstance(per_domain, dict) else {},
        }

        # Analyze costs
        primary_model = primary.get("model", "")
        fallback_model = fallback.get("model", "")
        cost_saving_model = cost_saving.get("model", "")

        for label, model_name in [
            ("primary", primary_model),
            ("fallback", fallback_model),
            ("cost_saving", cost_saving_model),
        ]:
            meta = MODEL_META.get(model_name, {})
            if meta:
                suggestions.append({
                    "role": label,
                    "model": model_name,
                    "provider": meta.get("provider", "deepseek"),
                    "tier": meta.get("tier", "unknown"),
                    "cost_per_m_input": meta.get("cost_per_m_input", 0),
                    "cost_per_m_output": meta.get("cost_per_m_output", 0),
                    "estimated_per_100k_input": round(meta.get("cost_per_m_input", 0) * 0.1, 4),
                    "estimated_per_100k_output": round(meta.get("cost_per_m_output", 0) * 0.1, 4),
                })

    # Add cost comparison
    cost_comparison = {}
    for model_name, meta in MODEL_META.items():
        if current_model == model_name:
            cost_comparison[model_name] = {
                "current": True,
                "provider": meta.get("provider", ""),
                "tier": meta.get("tier", ""),
                "cost_per_m_input": meta.get("cost_per_m_input", 0),
                "cost_per_m_output": meta.get("cost_per_m_output", 0),
            }
        else:
            cost_comparison[model_name] = {
                "current": False,
                "provider": meta.get("provider", ""),
                "tier": meta.get("tier", ""),
                "cost_per_m_input": meta.get("cost_per_m_input", 0),
                "cost_per_m_output": meta.get("cost_per_m_output", 0),
            }

    # Generate recommendation text
    current_tier = MODEL_META.get(current_model, {}).get("tier", "unknown")
    current_cost_in = MODEL_META.get(current_model, {}).get("cost_per_m_input", 0)
    current_cost_out = MODEL_META.get(current_model, {}).get("cost_per_m_output", 0)

    budget_opts = [
        (n, m) for n, m in MODEL_META.items()
        if m.get("tier") in ("budget", "standard")
    ]
    cheapest = min(budget_opts, key=lambda x: x[1].get("cost_per_m_input", 999)) if budget_opts else None

    recommendation = (
        f"Current model: {current_model} ({current_tier}, ${current_cost_in:.2f}/M in, "
        f"${current_cost_out:.2f}/M out). "
    )

    if cheapest and cheapest[0] != current_model:
        recommendation += (
            f"For cost savings, switch to {cheapest[0]} "
            f"(${cheapest[1]['cost_per_m_input']:.2f}/M in, ${cheapest[1]['cost_per_m_output']:.2f}/M out). "
        )

    if chain_result.get("fallback"):
        fb = chain_result["fallback"]
        recommendation += (
            f"Failover chain configured: primary={chain_result['primary'].get('model','?')} -> "
            f"fallback={fb.get('model','?')} -> "
            f"cost-saving={chain_result['cost_saving'].get('model','?')}"
        )

    return {
        "current_model": current_model,
        "current_provider": current_provider,
        "recommendation": recommendation,
        "cost_comparison": cost_comparison,
        "failover_chain": chain_result,
        "suggestions": suggestions,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hermes model router config — manage model routing and failover chains."
    )
    parser.add_argument(
        "action",
        nargs="?",
        choices=["show", "validate", "suggest"],
        default="show",
        help="Action to perform",
    )
    parser.add_argument(
        "--config", default=HERMES_CONFIG,
        help=f"Path to Hermes config.yaml (default: {HERMES_CONFIG})",
    )
    parser.add_argument(
        "--failover-chain", default=None,
        help="Path to failover-chain.yaml (default: references/failover-chain.yaml)",
    )
    parser.add_argument(
        "--pretty", action="store_true",
        help="Pretty-print JSON output",
    )
    args = parser.parse_args()

    config = read_config(args.config)

    if args.action == "show":
        result = action_show(config)
    elif args.action == "validate":
        result = action_validate(config)
    elif args.action == "suggest":
        result = action_suggest(config, args.failover_chain)
    else:
        print(f"error: unknown action '{args.action}'", file=sys.stderr)
        sys.exit(1)

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    main()
