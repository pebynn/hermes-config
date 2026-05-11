# Hermes 自定义 MCP 服务器清单

部署路径：`~/.hermes/mcp-servers/`
注册位置：`~/.hermes/config.yaml` → `mcp_servers` 段
运行引擎：`~/.hermes/hermes-agent/venv/bin/python3` (stdio MCP)

## 服务器列表

### 1. web-search (mcp-web-search.py)
- **工具**: `web_search(query: str, limit: int = 5)`
- **描述**: 通过 Tavily API 执行网络搜索，返回标题+URL+摘要
- **依赖**: TAVILY_API_KEY 环境变量
- **超时**: 默认

### 2. web-extract (mcp-web-extract.py)
- **工具**: `extract_url(url: str)`, `extract_bulk(urls: list[str])`
- **描述**: URL 内容提取。优先用 Jina Reader (r.jina.ai)，失败回退到 Crawl4AI
- **依赖**: Crawl4AI 0.8.6 (Hermes venv)
- **超时**: 120s

### 3. whisper-stt (mcp-whisper.py)
- **工具**: `transcribe_file(path: str)`, `transcribe_url(url: str)`
- **描述**: 语音转文字。调用 whisper CLI (model=base)
- **依赖**: openai-whisper (系统 Python + torch)
- **超时**: 360s

### 4. graphify (mcp-graphify.py)
- **工具**: `graph_search`, `graph_find_path`, `graph_explain`, `graph_stats`
- **描述**: 查询知识图谱 (112n/129e)。内置 BFS 路径查找
- **依赖**: ~/brain/graphify-out/graph.json
- **注意**: 内存缓存 _graph_data，修改 graph.json 后需新会话才能读到更新

### 5. llm-wiki (mcp-llm-wiki.py)
- **工具**: `wiki_search`, `wiki_read`, `wiki_list`
- **描述**: 查询 gbrain LLM Wiki 知识库
- **依赖**: ~/brain/ 目录（通过 gbrain CLI）

### 6. deep-research (mcp-deep-research.py)
- **工具**: `deep_research(question: str)`
- **描述**: 多角度并行调研 → 合成结构化报告
- **依赖**: TAVILY_API_KEY 环境变量
- **超时**: 180s

### 7. skill-auditor (mcp-skill-auditor.py) — 技能安全审计
- **工具**: `audit_skill(path, strict=False)`, `audit_skills_batch(paths)`
- **描述**: 外部技能安装前的安全审计闸门。4层检测（代码执行/Prompt注入/依赖供应链/文件系统），返回 PASS/WARN/FAIL 判定
- **来源**: 封装 claude-skills/engineering/skills/skill-security-auditor，通过 subprocess 调用本地脚本
- **依赖**: ~/.hermes/skills/security/skill-security-auditor/scripts/skill_security_auditor.py
- **超时**: 60s
- **硬约束**: CRITICAL 判定 → 禁止安装。主 SOUL.md 已将文本规则升级为 MCP 硬约束

### 8. security-auditor (mcp-security-auditor.py)
- **工具**: `scan_file(path)`, `scan_directory(path)`, `check_file_permissions(path)`
- **描述**: 通用安全审计。扫描 API 密钥泄露 (20+ 正则)、危险调用 (eval/exec/shell=True)、权限问题
- **依赖**: 无
- **超时**: 默认

### 9. hermes-delegate (mcp-hermes-delegate.py)
- **工具**: `delegate`, `check_task`, `list_tasks`
- **描述**: 外部 AI Agent 通过 MCP 向 Hermes 提交任务队列
- **依赖**: ~/.hermes/mcp-tasks/ 目录

### 10. hermes-cron (mcp-hermes-cron.py)
- **工具**: `cron_list`, `cron_create`, `cron_pause`, `cron_resume`, `cron_remove`, `cron_status`
- **描述**: Hermes 定时任务管理，封装 `hermes cron` CLI
- **依赖**: Hermes CLI

## 验证命令

```bash
# 查看自定义 MCP 进程数
ps aux | grep 'mcp-' | grep -v grep | grep '\.py' | wc -l

# 检查错误
tail -50 ~/.hermes/logs/mcp-stderr.log | grep -i 'error\|traceback\|exception'
```

## 构建模式

### 模式 A: 内联逻辑（标准骨架）
工具逻辑直接在 call_tool() 中实现，适合新开发的服务。
示例: web-search, graphify, llm-wiki

### 模式 B: CLI 封装（subprocess 包装）
封装已有 CLI 脚本，通过 subprocess.run() 调用并解析 JSON/文本输出。
适合将现有 Python 脚本快速 MCP 化。
示例: skill-auditor (封装 skill_security_auditor.py), hermes-cron (封装 `hermes cron` CLI)

关键代码：
```python
def run_audit(path: str, strict: bool = False) -> dict:
    cmd = ["python3", AUDITOR_SCRIPT, path, "--json"]
    if strict: cmd.append("--strict")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)
```

### MCP 协议验证三步法
```python
# 1. initialize (必须先于任何其他请求)
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{...}}
# 2. initialized notification
{"jsonrpc":"2.0","method":"notifications/initialized"}
# 3. 正常调用
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
```
