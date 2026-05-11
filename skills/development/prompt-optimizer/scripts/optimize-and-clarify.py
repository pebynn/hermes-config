#!/usr/bin/env python3
"""optimize-and-clarify — merged prompt-optimizer + task-clarify in one pass.

Raw user instruction → optimize(clarity+structure) → extract(domain/priority/constraints)
→ single JSON output ready for delegate_task.

Replaces: prompt-optimizer (standalone) + task-clarify.py (standalone)
"""

import argparse
import json
import re
import sys


# =============================================================================
# Domain inference (from task-clarify.py)
# =============================================================================

DOMAIN_RULES = [
    (r"(?:股票|量化|回测|因子|选股|A股|估值|投资|基本面|财报|k[线圖]|行情|交易|持仓|盈亏|缠论|资金流|择时)", "finance"),
    (r"(?:选品|上架|订单|电商|pdd|拼多多|17网|女装|套装|运营|listing|sourcing|fulfillment|退货|定价|款式)", "ec"),
    (r"(?:研究|分析|调研|报告|research|竞品|市场趋势|深度|挖一挖|找找看|调研|调查)", "research"),
    (r"(?:部署|deploy|安装|install|配置|cron|定时|运维|docker|server|后台|监控|重启|重启服务)", "ops"),
    (r"(?:写|改|修|代码|code|bug|git|commit|pr|python|脚本|script|重构|refactor|测试|test|debug|fix|patch|修复|类型错误)", "code"),
]


def infer_domain(text: str) -> str:
    text_clean = re.sub(r"(?:不要|别|不)(?:改|修|动)", "", text, flags=re.IGNORECASE)
    for pattern, domain in DOMAIN_RULES:
        if re.search(pattern, text_clean, re.IGNORECASE):
            return domain
    return "general"


def infer_priority(text: str) -> str:
    if re.search(r"(?:紧急|urgent|立刻|马上|fix|修复|bug|crash|挂了|停)", text, re.IGNORECASE):
        return "P0"
    if re.search(r"(?:重要|必须|一定|今天|immediate)", text, re.IGNORECASE):
        return "P1"
    return "P2"


def extract_constraints(text: str) -> list[str]:
    constraints = []
    patterns = [
        (r"不要[改修](\S*)", "no-modify"),
        (r"只[看查](\S*)", "read-only"),
        (r"不[改修动](\S*)", "no-modify"),
        (r"仅分[析析]", "analysis-only"),
        (r"只读", "read-only"),
        (r"别[改修]", "no-modify"),
    ]
    for pat, const in patterns:
        if re.search(pat, text, re.IGNORECASE):
            constraints.append(const)
    return list(set(constraints)) if constraints else ["none-specified"]


def suggest_output(text: str, domain: str) -> str:
    fmt = {
        "code": "code diff or file path",
        "ec": "action report with URLs/prices/status",
        "research": "markdown report with findings + sources",
        "finance": "structured analysis with metrics/conclusion",
        "ops": "execution log with status",
        "general": "concise answer with actionable next step",
    }
    return fmt.get(domain, fmt["general"])


# =============================================================================
# Prompt optimization (from prompt-optimizer skill)
# =============================================================================

def analyze_raw(text: str) -> dict:
    """Identify clarity/structure/specificity gaps in the raw input."""
    issues = []

    # Clarity: check for ambiguous pronouns, missing objects
    if re.search(r"^(?:这个|那个|它|他|她|这|那)[\s，。]", text):
        issues.append("ambiguous_reference")
    if len(text) < 10:
        issues.append("too_short")

    # Specificity: check for missing quantifiers
    has_numbers = bool(re.search(r"\d+", text))
    has_constraints = bool(re.search(r"(?:不要|别|不|只|仅|必须|一定|限制)", text))
    if not has_numbers and not has_constraints and len(text) > 20:
        issues.append("lacks_specificity")

    # Structure: check if multi-step but flat
    steps = re.findall(r"(?:第[一二三四五六七八九十\d]+[步]|[1-9]\d*[.、])", text)
    has_multi = bool(re.search(r"(?:然后|接着|之后|再|同时|并且)", text))
    if has_multi and not steps:
        issues.append("multi_step_flat")

    return {"issues": issues, "has_numbers": has_numbers, "has_multi_step": has_multi}


def optimize(text: str) -> str:
    """Apply prompt optimization: disambiguate, structure, add missing context.

    Returns the optimized instruction text.
    """
    analysis = analyze_raw(text)

    # If already well-structured, return as-is
    if not analysis["issues"]:
        return text

    optimized = text.strip()

    # --- Clarity fixes ---
    # Replace ambiguous starters
    optimized = re.sub(r"^(这个|那个|它|他|她)\s*", lambda m: f"上述{m.group(1)}", optimized)

    # --- Structure fixes ---
    # If multi-step but no numbering, auto-number with bullet points
    if analysis["has_multi_step"]:
        parts = re.split(r"(?:然后|接着|之后|再|同时|并且)", optimized)
        if len(parts) > 1:
            cleaned = []
            for i, part in enumerate(parts, 1):
                part = part.strip().rstrip("，。；;")
                if part:
                    cleaned.append(f"{i}. {part}")
            optimized = "\n".join(cleaned)

    # --- Specificity fixes ---
    # Add explicit deliverable if missing
    has_deliverable = re.search(r"(?:输出|产出|保存到|写入|生成|创建|报告|文件|commit)", optimized)
    if not has_deliverable and not analysis["has_numbers"]:
        optimized += "。输出结果到终端。"

    return optimized


# =============================================================================
# Main pipeline
# =============================================================================

def pipeline(raw: str) -> dict:
    """Run optimize → extract in one pass, output unified spec."""
    optimized_prompt = optimize(raw)

    domain = infer_domain(optimized_prompt)
    priority = infer_priority(optimized_prompt)
    constraints = extract_constraints(optimized_prompt)
    output_fmt = suggest_output(optimized_prompt, domain)

    # Core goal: first sentence of optimized prompt
    goal = optimized_prompt.strip().split("。")[0].split("\n")[0].strip()
    if len(goal) > 120:
        goal = goal[:117] + "..."

    # Named entities
    paths = re.findall(r"~?/[^\s,，。；;]+", optimized_prompt)

    return {
        "optimized_prompt": optimized_prompt,
        "goal": goal,
        "domain": domain,
        "priority": priority,
        "constraints": constraints,
        "expected_output": output_fmt,
        "context": {
            "raw_input": raw.strip(),
            "paths_referenced": paths,
            "improvements_applied": analyze_raw(raw)["issues"],
        },
    }


def main():
    ap = argparse.ArgumentParser(description="Optimize + clarify in one pass")
    ap.add_argument("input", nargs="?", help="Raw task text (stdin if omitted)")
    ap.add_argument("--json", action="store_true", help="JSON output only")
    args = ap.parse_args()

    raw = args.input or sys.stdin.read().strip()
    if not raw:
        print('{"error":"no input"}', file=sys.stderr)
        sys.exit(1)

    spec = pipeline(raw)

    if args.json:
        print(json.dumps(spec, ensure_ascii=False, indent=2))
    else:
        print(f"Domain:     {spec['domain']}")
        print(f"Priority:   {spec['priority']}")
        print(f"Goal:       {spec['goal']}")
        print(f"Output:     {spec['expected_output']}")
        if spec["constraints"] != ["none-specified"]:
            print(f"Constraints:{', '.join(spec['constraints'])}")
        if spec["context"]["improvements_applied"]:
            print(f"Improved:   {', '.join(spec['context']['improvements_applied'])}")
        print()
        print("--- Optimized prompt ---")
        print(spec["optimized_prompt"])
        print()
        print("--- JSON payload ---")
        print(json.dumps(spec, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
