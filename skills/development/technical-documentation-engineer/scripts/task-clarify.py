#!/usr/bin/env python3
"""task-clarify — transform raw user requests into structured agent-executable task specs.

Reads raw text from stdin or file, outputs a JSON task spec with:
  Goal: what to accomplish (one sentence)
  Context: paths, constraints, background
  Constraints: hard limits (no-modify, data-only, etc.)
  Expected: concrete deliverable format
  Domain: inferred domain (code/ec/research/finance/ops/general)
  Priority: P0/P1/P2
"""

import argparse
import json
import re
import sys


def parse_args():
    p = argparse.ArgumentParser(
        description="Clarify a raw task into agent-executable format"
    )
    p.add_argument(
        "input", nargs="?", default=None,
        help="Raw task text (reads stdin if omitted)"
    )
    p.add_argument(
        "--json", action="store_true",
        help="Output JSON only (default: human-readable)"
    )
    p.add_argument(
        "--domain-hint", default=None,
        help="Force a domain override (code|ec|research|finance|ops|general)"
    )
    return p.parse_args()


def infer_domain(text: str, hint: str | None = None) -> str:
    """Infer which Hermes domain should handle this task."""
    if hint:
        return hint

    # Strip negation context: "不要改/别改/不改" should not trigger code domain
    text_clean = re.sub(r"(?:不要|别|不)(?:改|修|动)", "", text, flags=re.IGNORECASE)

    rules = [
        (r"(?:股票|量化|回测|因子|选股|A股|估值|投资|基本面|财报|k[线圖]|行情|交易|持仓|盈亏)", "finance"),
        (r"(?:选品|上架|订单|电商|pdd|拼多多|17网|女装|套装|运营|listing|sourcing|fulfillment|退货|定价|款式)", "ec"),
        (r"(?:研究|分析|调研|报告|research|竞品|市场趋势|深度|挖一挖|找找看)", "research"),
        (r"(?:部署|deploy|安装|install|配置|cron|定时|运维|docker|server|后台|监控)", "ops"),
        (r"(?:写|改|修|代码|code|bug|git|commit|pr|python|脚本|script|重构|refactor|测试|test|debug|fix|patch)", "code"),
    ]
    for pattern, domain in rules:
        if re.search(pattern, text_clean, re.IGNORECASE):
            return domain
    return "general"


def infer_priority(text: str) -> str:
    """Infer task priority."""
    urgent = re.search(r"(?:紧急|urgent|立刻|马上|fix|修复|bug|crash|挂了)", text, re.IGNORECASE)
    important = re.search(r"(?:重要|必须|一定|今天|immediate)", text, re.IGNORECASE)
    if urgent:
        return "P0"
    if important:
        return "P1"
    return "P2"


def extract_constraints(text: str) -> list[str]:
    """Extract hard constraints from the request."""
    constraints = []
    patterns = [
        (r"不要[改修](\S+)", "no-modify"),
        (r"只[看查](\S+)", "read-only"),
        (r"不[改修动](\S+)", "no-modify"),
        (r"仅分[析析]", "analysis-only"),
        (r"只读", "read-only"),
        (r"别[改修]", "no-modify"),
    ]
    for pat, const in patterns:
        if re.search(pat, text, re.IGNORECASE):
            constraints.append(const)

    if not constraints:
        constraints.append("none-specified")

    return list(set(constraints))


def suggest_output_format(text: str, domain: str) -> str:
    """Suggest expected output format."""
    fmt_map = {
        "code": "code diff or file path",
        "ec": "action report with URLs/prices/status",
        "research": "markdown report with findings + sources",
        "finance": "structured analysis with metrics/conclusion",
        "ops": "execution log with status",
        "general": "concise answer with actionable next step",
    }
    return fmt_map.get(domain, fmt_map["general"])


def clarify(raw: str, domain_hint: str | None = None) -> dict:
    """Parse raw request into structured task spec."""
    domain = infer_domain(raw, domain_hint)

    # Extract the core goal: first sentence or key action
    goal = raw.strip().split("。")[0].split("\n")[0].strip()
    if len(goal) > 120:
        goal = goal[:117] + "..."

    # Detect named entities (paths, repos, skills)
    paths = re.findall(r"~?/[^\s,，。；;]+", raw)
    skills = re.findall(r"(?:skill|技能)[：:\s]*(\S+)", raw, re.IGNORECASE)

    return {
        "goal": goal,
        "context": {
            "raw_input": raw.strip(),
            "paths_referenced": paths,
            "skills_referenced": skills,
        },
        "constraints": extract_constraints(raw),
        "expected_output": suggest_output_format(raw, domain),
        "domain": domain,
        "priority": infer_priority(raw),
    }


def main():
    args = parse_args()

    if args.input:
        raw = args.input
    else:
        raw = sys.stdin.read().strip()

    if not raw:
        print("Error: no input provided", file=sys.stderr)
        sys.exit(1)

    spec = clarify(raw, args.domain_hint)

    if args.json:
        print(json.dumps(spec, ensure_ascii=False, indent=2))
    else:
        print(f"Domain:   {spec['domain']}")
        print(f"Priority: {spec['priority']}")
        print(f"Goal:     {spec['goal']}")
        print(f"Output:   {spec['expected_output']}")
        if spec["constraints"] and spec["constraints"] != ["none-specified"]:
            print(f"Limits:   {', '.join(spec['constraints'])}")
        if spec["context"]["paths_referenced"]:
            print(f"Paths:    {', '.join(spec['context']['paths_referenced'])}")
        if spec["context"]["skills_referenced"]:
            print(f"Skills:   {', '.join(spec['context']['skills_referenced'])}")

        print()
        print("--- Structured delegation payload ---")
        print(json.dumps(spec, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
