#!/usr/bin/env python3
"""Config guard: 检测关键配置漂移，异常时告警。
Run as cron (e.g., daily at 10:00). Silent if OK.
"""
import yaml
from pathlib import Path

CONFIG = Path.home() / ".hermes" / "config.yaml"
RULES = {
    "compression.enabled": {
        "must": False,
        "reason": "内置压缩引擎 orphan tool_calls bug → DeepSeek 400",
        "severity": "CRITICAL",
    },
    "compression.threshold": {
        "max": 0.9,
        "reason": "过高阈值=几乎不压缩，失去保护意义",
    },
}

def get_nested(d, path):
    for k in path.split("."):
        if isinstance(d, dict):
            d = d.get(k)
        else:
            return None
    return d

def main():
    if not CONFIG.exists():
        return  # no config, skip

    try:
        config = yaml.safe_load(CONFIG.read_text())
    except Exception:
        return

    violations = []
    for path, rule in RULES.items():
        val = get_nested(config, path)
        if val is None:
            continue

        must = rule.get("must")
        if must is not None and val != must:
            violations.append(
                f"[{rule['severity']}] {path} = {val}, must be {must}"
                f"\n  reason: {rule['reason']}"
            )

        max_val = rule.get("max")
        if max_val is not None and isinstance(val, (int, float)) and val > max_val:
            violations.append(
                f"[WARN] {path} = {val} > max {max_val}"
            )

    if violations:
        print("CONFIG GUARD: 配置漂移检测")
        for v in violations:
            print(v)

if __name__ == "__main__":
    main()
