---
name: native-mcp
description: Hermes Agent 内置 MCP 客户端 — 配置/排障不同传输类型的 MCP 服务器（stdio/HTTP）。含实战配方：time/github/database/sequential-thinking
version: "1.1.0"
author: "seaworld008 + local"
source: "Commonly-used-high-value-skills + 实战经验"
tags: ["mcp", "hermes", "client", "integration", "troubleshooting"]
created_at: "2026-03-18"
updated_at: "2026-05-09"
---
# Native MCP Client

Hermes Agent 内置的 MCP 客户端。配置 `config.yaml` 的 `mcp_servers` 段后，自动发现外部 MCP 服务器的工具并注册为 Hermes 原生工具。

> 无需桥接 CLI — MCP 工具与内置工具（terminal/read_file 等）同级出现。

## 前置条件

```bash
pip install mcp
```

需要 Node.js（用于 npx 启动的服务），`uvx` 在 Hermes venv 中已可用。

## 传输类型与配置模板

### Stdio 传输（本地进程）

服务通过子进程启动，生命周期由 Hermes 管理。

```yaml
mcp_servers:
  server_name:
    command: "uvx"              # 或 "npx"
    args: ["package-name"]      # uvx: 无需 -y；npx: 需 -y
    env:                        # 可选，显式传递环境变量
      SOME_KEY: "value"
    timeout: 120                # 单次工具调用超时
    connect_timeout: 60         # 连接超时
```

**常见启动命令对照：**

| 语言 | 命令 | 示例 |
|------|------|------|
| Python | `uvx` | `uvx mcp-server-time` |
| TypeScript/JS | `npx -y` | `npx -y @modelcontextprotocol/server-sequential-thinking` |
| 带参数 | 追加到 args | `npx -y @berthojoris/mcp-mysql-server mysql://user:pass@host:3306/db` |

### HTTP 传输（远程服务）

服务通过 URL 连接，无需本地安装。

```yaml
mcp_servers:
  server_name:
    url: "https://api.example.com/mcp"
    headers:
      Authorization: "Bearer ${TOKEN}"
    timeout: 180
```

HTTP 服务不会在 `mcp-stderr.log` 中产生日志，连接成功/失败在 agent 启动时静默处理。

## 实战配方

### Time — 最简单的入门示例
```yaml
mcp_servers:
  time:
    command: "uvx"
    args: ["mcp-server-time"]
```
提供 ~6 个时间相关工具（时区转换、日期计算等）。

### GitHub — 官方 HTTP 服务（需 GITHUB_TOKEN）
```yaml
mcp_servers:
  github:
    url: "https://api.githubcopilot.com/mcp/"
    headers:
      Authorization: "Bearer ${GITHUB_TOKEN}"
      User-Agent: "hermes-agent/1.0"
```
提供 ~45 个 GitHub API 工具。token 从 github.com/settings/tokens 生成，需 `repo` + `read:org` 权限。
⚠️ 注意：`uvx mcp-server-github` 这个包不存在，必须用 HTTP 方式。

### MySQL — 直接查本地数据库
```yaml
mcp_servers:
  mysql:
    command: "npx"
    args: ["-y", "@berthojoris/mcp-mysql-server", "mysql://user:password@localhost:3306/database"]
```
提供 ~20+ 个数据库工具（查询/表结构/分析）。连接串格式：`mysql://user:pass@host:port/db`

### 自定义 Python MCP 服务器 — Hermes 内部能力包装

使用 Python MCP SDK 将 Hermes 内部能力包装为 MCP 服务器，供外部 MCP 客户端使用。

```yaml
mcp_servers:
  server-name:
    command: "/home/pebynn/.hermes/hermes-agent/venv/bin/python3"
    args: ["/home/pebynn/.hermes/mcp-servers/mcp-server-name.py"]
    timeout: 120          # 可选
```

标准存放路径：`~/.hermes/mcp-servers/`
标准运行引擎：Hermes venv Python（mcp SDK 在其中）

⚠️ SDK v1.27+ 注意事项：
- `Server.run()` 需要 `InitializationOptions` 作为第四个参数
- `from mcp.types import ServerCapabilities, ToolsCapability`（**NOT** from mcp.shared.capabilities）
- 正确骨架见 `development/mcp-builder` 技能

当前部署的 10 个自定义 MCP 服务器清单见 `development/mcp-builder/references/hermes-custom-mcp-servers.md`

### Sequential Thinking — 结构化推理
```yaml
mcp_servers:
  sequential-thinking:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-sequential-thinking"]
```
提供一个 `sequential_thinking` 工具，用于复杂问题分步拆解推理。

## Standalone 脚本调用 MCP（JSON-RPC 桥接）

MCP 工具默认只在 agent 会话中可用。如果需要在 cron 脚本或后台服务中调用 MCP 工具，可通过子进程 + JSON-RPC 协议建立桥接：

```python
from subprocess import Popen, PIPE
import json

proc = Popen(["/path/to/mcp-server"], stdin=PIPE, stdout=PIPE)
# 发送 initialize + tools/call JSON-RPC 请求
# 从 stdout 读取 JSON 响应解析工具结果
```

**核心步骤**：
1. 启动 MCP Server 子进程
2. 发送 `initialize` 请求
3. 发送 `notifications/initialized` 通知
4. 发送 `tools/call` 请求（含 tool_name + arguments）
5. 读取 stdout 一行 JSON → 解析 `result.content[0].text`
6. 终止子进程

**陷阱**：
- 每个调用启动新进程（适合低频调用，<10次/min）
- stderr 管道填满会死锁 → 加 stderr=DEVNULL 或读取线程
- MCP Server 可能需要先发送 `ListTools` 再 `CallTool`

**详见** `references/mcp-jsonrpc-bridge-pattern.md`
**实战案例**: `~/writing-data/scripts/shared/stock_sdk_client.py` — 365行，通过此模式调用 stock-sdk-mcp 获取美股/恒生/A50行情

## 安全

- Stdio 子进程仅接收 PATH/HOME/USER 等安全基线变量
- API Key/Token 除非在 `env` 中显式配置，否则不传递给子进程
- 错误消息自动脱敏 `sk-*`、`ghp_*` 等凭证模式
- 数据库 MCP 的连接串含密码，确保 `.env` 和 `config.yaml` 权限正确

## 参考

- `references/openclaw-mcp-bridge.md` — OpenClaw MCP 桥接完整安装流程（Playwright浏览器沙箱，解决React/隐身/持久登录）
- `references/mysql-password-update.md` — MySQL MCP 密码变更完整流程（含陷阱和排障）
- `references/mcp-jsonrpc-bridge-pattern.md` — Standalone 脚本调用 MCP 工具：子进程 + JSON-RPC 协议桥接。含完整实现、陷阱清单。实战案例：stock_sdk_client.py

## 故障排查

| 现象 | 原因 | 修复 |
|------|------|------|
| `No solution found when resolving tool dependencies` | npm/PyPI 包名不存在 | 搜索正确包名，或改用 HTTP 方式 |
| `Package X was not found in the package registry` | 包名错误或未发布 | 核实 npmjs.com 或 pypi.org 上的包名 |
| MCP 工具未出现在当前会话 | 服务在会话启动后才添加 | 重启 gateway 后开新会话 |
| HTTP 服务无日志、无通知 | HTTP MCP 静默连接 | 检查 gateway.log 或尝试访问 URL 看是否可达 |
| 数据库 MCP 连接失败 | 连接串格式错误或密码有特殊字符 | 确保 URL-encode 密码中的特殊字符 |
| 数据库 MCP 改密码后仍连不上 | 旧 MCP 进程未随 gateway 重启而终止，仍用旧密码 | `pkill -f 'mcp-mysql'` 杀干净 → gateway 自动重建新进程（~40s 就绪） |
| 配置写 `${ENV_VAR}` MCP 连不上 | MCP stdio 传输 args 不做 shell 展开，`${VAR}` 被当字面量传给子进程 | 用明文密码或通过 `env:` 字段传变量给 MCP 进程 |
| 工具前缀不是预期名称 | MCP 服务器名用作前缀 | `mcp_{config_key}_{tool_name}` |

## 验证步骤

配置新 MCP 服务器后：

1. 重启 gateway：`systemctl --user restart hermes-gateway.service`
2. 检查 stderr 日志：`tail -20 ~/.hermes/logs/mcp-stderr.log`
3. 确认进程运行：`ps aux | grep -E 'mcp-server|npx.*mcp' | grep -v grep`
4. 新会话中工具以 `mcp_*` 前缀出现在工具列表

## 边界

- 每个 MCP 服务器在独立线程中运行
- 失败服务器自动重试（指数退避，最多 5 次）
- 此技能描述 Hermes 已有功能，非需要额外安装的工具
- 非官方/社区 MCP 服务器有安全风险，建议先用 skill-vetter 扫描
