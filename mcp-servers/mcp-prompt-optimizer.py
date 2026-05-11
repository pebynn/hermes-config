#!/usr/bin/env python3
"""
MCP server: prompt-optimizer
Hard-wires the optimize-and-clarify step into the instruction pipeline.

Tools:
  - optimize_prompt(text) → {domain, priority, constraints, optimized_prompt}
  - infer_domain(text)     → domain string
  - infer_priority(text)   → priority string

Usage:
  python3 mcp-prompt-optimizer.py
"""
import asyncio
import json
import re
import sys
import os

# Import the core logic from optimize-and-clarify.py
OPTIMIZER_PATH = os.path.expanduser(
    "~/.hermes/skills/development/prompt-optimizer/scripts/optimize-and-clarify.py"
)
sys.path.insert(0, os.path.dirname(OPTIMIZER_PATH))

# Inline the core functions to avoid import issues
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

def extract_constraints(text: str) -> list:
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


# Prompt optimization heuristics
def optimize_prompt_text(text: str) -> str:
    """Apply prompt engineering best practices to clarify and structure the prompt."""
    optimized = text.strip()
    
    # Remove filler words
    filler_patterns = [
        r"能不能(?:帮我|帮忙|给我)",
        r"(?:你能不能|你可以|你可不可以)",
        r"(?:我想|我想要|我需要|我要)",
        r"(?:麻烦|请)(?:你|您)",
    ]
    for pat in filler_patterns:
        optimized = re.sub(pat, "", optimized)
    
    # Ensure imperative mood for action tasks
    action_keywords = ["修复", "写", "改", "部署", "安装", "配置", "分析", "生成", "创建"]
    if any(kw in optimized for kw in action_keywords) and not any(
        optimized.startswith(kw) for kw in action_keywords
    ):
        # Already has action verb, keep as-is
        pass
    
    optimized = re.sub(r"\s+", " ", optimized).strip()
    return optimized


from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("prompt-optimizer")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="optimize_prompt",
            description="Optimize and clarify a raw user instruction. Returns domain, priority, constraints, and optimized prompt text. MUST be called before delegate_task in the instruction pipeline.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Raw user instruction text to optimize",
                    },
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="infer_domain",
            description="Infer which domain (code/ec/ops/research/finance/general) a user instruction belongs to.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "User instruction text"},
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="infer_priority",
            description="Infer priority level (P0/P1/P2) from user instruction urgency signals.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "User instruction text"},
                },
                "required": ["text"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "optimize_prompt":
        text = arguments["text"]
        result = {
            "domain": infer_domain(text),
            "priority": infer_priority(text),
            "constraints": extract_constraints(text),
            "optimized_prompt": optimize_prompt_text(text),
        }
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "infer_domain":
        text = arguments["text"]
        return [TextContent(type="text", text=json.dumps({"domain": infer_domain(text)}, ensure_ascii=False))]

    elif name == "infer_priority":
        text = arguments["text"]
        return [TextContent(type="text", text=json.dumps({"priority": infer_priority(text)}, ensure_ascii=False))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
