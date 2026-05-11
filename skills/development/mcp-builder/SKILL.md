---
name: mcp-builder
description: 构建高质量 MCP (Model Context Protocol) Server 的分步指南。覆盖 Python SDK v1.27+，含工具设计/认证/测试/Hermes集成/排障全流程
version: "2.0.0"
author: "seaworld008 + local"
source: "Commonly-used-high-value-skills + 实战经验"
tags: ["mcp", "server", "protocol", "tool-building", "python", "hermes"]
created_at: "2026-03-18"
updated_at: "2026-05-01"
---
# MCP Server 开发指南

构建高质量 MCP Server，使 LLM 能通过结构化工具与外部服务交互。

## 前置条件

```bash
pip install mcp  # Python SDK，Hermes venv 中已安装
```

需要 Node.js（用于 npx 启动的服务），`uvx` 在 Hermes venv 中已可用。

## SDK 兼容性速查

当前 Hermes venv 中的 MCP Python SDK 版本要求（v1.27+）：

| 模式 | 代码 | 说明 |
|------|------|------|
| ✅ 正确 | `from mcp.server.models import InitializationOptions` | SDK v1.27+ 必需 |
| ✅ 正确 | `from mcp.types import ServerCapabilities, ToolsCapability` | **NOT** from `mcp.shared.capabilities` — 该路径不存在 |
| ✅ 正确 | `await server.run(read, write, InitializationOptions(...))` | 4个必选参数 |
| ❌ 错误 | `await server.run(read, write)` | 缺少 initialization_options，报 TypeError |
| ❌ 错误 | `from mcp.shared.capabilities import ToolsCapability` | ModuleNotFoundError |

## 标准 Python 服务器骨架

```python
#!/usr/bin/env python3
"""MCP Server: server-name — 简短描述"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities, ToolsCapability

server = Server("server-name")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="tool_name",
            description="工具描述",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "参数说明"},
                },
                "required": ["param1"],
            },
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "tool_name":
        param = arguments.get("param1")
        # 执行逻辑...
        return [TextContent(type="text", text=f"结果: {result}")]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read, write):
        await server.run(
            read, write,
            InitializationOptions(
                server_name="server-name",
                server_version="1.0.0",
                capabilities=ServerCapabilities(tools=ToolsCapability(list_changed=True)),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
```

## 四阶段工作流

### Phase 1: 研究与规划
- 理解工具命名规范（`web_search_query` 风格，小写+下划线）
- 学习 MCP 协议：https://modelcontextprotocol.io/specification/draft
- 确定传输方式：stdio（本地进程）或 HTTP（远程服务）
- 确定 API 认证方案（环境变量 / 配置文件）
- **判断构建模式**：新开发 → 模式 A（内联逻辑）；封装已有 CLI → 模式 B（subprocess 包装）

### Phase 2: 实现

**模式 A — 内联逻辑**（标准骨架适用）：
- 使用 Python 骨架，确保导入路径正确
- 每个工具定义清晰的 inputSchema 和 description
- 对 API 调用做错误处理，返回 TextContent 而非抛出异常
- **不需要外部 HTTP 库** — stdio 传输用 `urllib.request` 即可

**模式 B — CLI 封装**（subprocess 包装已有脚本）：
- 用 `subprocess.run()` 调用已有 CLI 脚本
- 脚本输出 JSON → 直接 `json.loads()` 解析
- 脚本输出文本 → 原样包装为 TextContent
- 必须设 `timeout` 防止子进程挂死
- 示例：`mcp-skill-auditor.py` 封装了 `skill_security_auditor.py`（980行 CLI 脚本）

```python
import subprocess, json

SCRIPT = os.path.expanduser("~/.hermes/skills/.../script.py")

def run_tool(path: str) -> dict:
    result = subprocess.run(
        ["python3", SCRIPT, path, "--json"],
        capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "my_tool":
        data = run_tool(arguments["path"])
        return [TextContent(type="text", text=json.dumps(data, indent=2))]
```

### Phase 3: 测试
- 语法检查：`python3 -m py_compile server.py`
- MCP Inspector：`npx @modelcontextprotocol/inspector`
- 在 Hermes 中注册并重启 gateway 后测试

### Phase 4: 部署到 Hermes
1. 将脚本放入 `~/.hermes/mcp-servers/`（标准路径）
2. 在 `~/.hermes/config.yaml` 的 `mcp_servers` 段添加条目
3. 重启 gateway：`systemctl --user restart hermes-gateway.service`
4. 验证进程：`ps aux | grep 'mcp-' | grep -v grep | grep '\.py'`
5. 验证日志：`tail -20 ~/.hermes/logs/mcp-stderr.log`

## 注册到 Hermes config.yaml

```yaml
mcp_servers:
  server-name:                    # MCP 服务器名，用作工具前缀 mcp_{name}_
    command: "/home/pebynn/.hermes/hermes-agent/venv/bin/python3"
    args: ["/home/pebynn/.hermes/mcp-servers/mcp-server-name.py"]
    timeout: 120                  # 可选，单次工具调用超时（秒）
    connect_timeout: 60           # 可选，连接超时
```

注意：
- 必须使用 Hermes venv 的 Python（`~/.hermes/hermes-agent/venv/bin/python3`），因为 `mcp` 包装在该 venv
- script 本身如果调用外部工具（whisper CLI、系统 Python），通过 subprocess 调用，不影响 MCP 框架
- timeout 对网络 IO 密集的服务器（web-search、web-extract）建议设 120-360s

## Hermes 自定义 MCP 服务器清单

参见 `references/hermes-custom-mcp-servers.md`，记录了系统当前部署的所有 10 个自定义 MCP 服务器。

## 故障排查

| 现象 | 原因 | 修复 |
|------|------|------|
| `TypeError: Server.run() missing 1 required positional argument` | SDK v1.27+ 需 InitializationOptions | 添加 `from mcp.server.models import InitializationOptions` 并传入 |
| `ModuleNotFoundError: No module named 'mcp.shared.capabilities'` | ToolsCapability 不在 shared 包 | `from mcp.types import ToolsCapability` |
| `NameError: name 'TextContent' is not defined` | 缺少类型导入 | 确保 `from mcp.types import Tool, TextContent, ServerCapabilities, ToolsCapability` |
| MCP 进程启动后立即消失 | 脚本运行时 import error | 用 `python3 -m py_compile` 检查语法，手动运行看报错 |
| MCP 工具未出现在当前会话 | 服务在会话启动后才添加 | 重启 gateway 后开新会话 |
| 多个重试重启同一失败 MCP | Hermes 指数退避重试（最多5次） | 检查 mcp-stderr.log 找到根因后才重启，否则重复失败 |

## 边界
- 不生成生产部署配置
- 不处理运行时监控
- 认证方案需根据具体 API 实现
- MCP 服务器只做 stdio 传输，不直接暴露 HTTP 端口
