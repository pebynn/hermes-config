# 知识管道端到端检查

memory → hindsight → gbrain → graphify → wiki 全链路诊断。

## 管道架构

```
memory (~/.hermes/memories/)
  → 每轮注入 system prompt，持久化用户偏好和关键事实
  ↓
hindsight (Docker: ghcr.io/vectorize-io/hindsight:latest)
  → 会话记忆向量化，Agent Memory That Works Like Human Memory
  → 端口: 8888(API) 9999(UI)，内嵌 PostgreSQL
  ↓
gbrain (cron 47600ff91a8f, 每6h)
  → 索引 ~/brain/ 下 markdown 文件，供 llm-wiki MCP 搜索
  ↓
graphify (cron e1917ae814df, 周一03:00)
  → AST+LLM语义提取 → NetworkX图 → Leiden聚类
  → 输出: ~/brain/graphify-out/graph.json
  ↓
wiki (~/brain/)
  → 知识库: index.md/log.md/schema.md + knowledge/lenses/methodology/projects/sources/
  → 域 SOUL 副本: ~/brain/soul/{code,ec,finance,ops,research,writing}-domain.md + hermes-main.md
  → 通过 llm-wiki MCP 搜索
```

## 检查清单

| 组件 | 方法 | 通过条件 |
|:-----|:-----|:---------|
| memory | `memory` 工具读/写/删一轮 | 读写删正常，usage<70% |
| hindsight | `docker ps --filter name=hindsight` | 容器 Up |
| hindsight API | `curl -s http://localhost:8888/health` | 返回 ok |
| gbrain | `cronjob list` 查 47600ff91a8f | last_status=ok |
| graphify 图存在 | `ls -lh ~/brain/graphify-out/graph.json` | 文件>0字节，节点>50 |
| graphify 边正常 | `python3 -c "import json; g=json.load(open('...')); print(len(g['edges']))"` | edges>0 |
| wiki 可搜索 | `mcp_llm_wiki_wiki_search topic="hermes"` | 返回结果非空 |
| wiki 域副本完整 | `ls ~/brain/soul/ | wc -l` | 7个文件 |
| lesson→graph 桥接 | `python3 -c "from scripts.lesson_graph_bridge import GRAPHIFY_BIN; print(GRAPHIFY_BIN)"` 在 ~/.hermes 下执行 | 非 None |
| 命名空间连通 | `mcp_graphify_graph_find_path(source="brain::brain_writing_domain", target=".hermes::hermes_writing-domain")` | 有路径（非"No path"） |
| lesson_inject 可用 | `python3 ~/.hermes/scripts/lesson_inject.py inject --domain writing-domain | head -3` | 返回教训块 |

## 常见故障

### hindsight 启动卡住（HuggingFace 下载超时）

**症状**: 容器 Up 但 `curl localhost:8888` 连接重置，日志停在 `Loading SentenceTransformer model from BAAI/bge-small-en-v1.5`

**根因**: 国内无 VPN 直连 huggingface.co 极慢/不通，下载 embedding 模型卡死。

**修复 A — HF 镜像**:
```bash
docker stop hindsight
# docker-compose.yml 加:
#   environment:
#     HF_ENDPOINT: https://hf-mirror.com
docker compose up -d
```

**修复 B — 跳过本地 embedding**:
改 docker-compose.yml 中 embedding provider 从 local 改为 API。

### graphify MCP 路径不匹配

**症状**: `mcp_graphify_graph_stats` 报 "Graph file not found: /tmp/hermes-graph/graphify-out/graph.json"

**根因**: mcp-graphify.py 硬编码 `GRAPH_PATH = "/tmp/hermes-graph/..."` 但实际图在 `~/brain/graphify-out/`

**修复**:
```bash
# 改 mcp-graphify.py 第 28 行:
# GRAPH_PATH = "/home/pebynn/brain/graphify-out/graph.json"
```
改后需 MCP 重载或 gateway 重启生效。

### graphify 0 条边

**症状**: `mcp_graphify_graph_stats` 返回 nodes=N, edges=0

**根因1 — 关系抽取失败**: 图构建时关系抽取失败（可能是 LLM 调用超时或内容不足）。
**根因2 — 字段名不匹配**: graphify 存边用 `links` 字段（非 `edges`），MCP server 可能查错字段。

**验证**: 
```bash
python3 -c "
import json
with open('/home/pebynn/brain/graphify-out/graph.json') as f:
    g = json.load(f)
print(f'nodes: {len(g.get(\"nodes\",[]))}, links: {len(g.get(\"links\",[]))}, edges: {len(g.get(\"edges\",[]))}')
"
```
如果 links>0 但 edges=0 → 字段名 bug，MCP server 需适配。

**修复1**: 重跑 graphify `graphify --update ~/brain/`
**修复2**: 改 MCP server 从查 `edges` 改为查 `links`

### wiki 搜索无结果

**症状**: `mcp_llm_wiki_wiki_search` 返回 "No matches found"

**检查**: gbrain 是否同步 → `cronjob list | grep gbrain`，确认 last_status=ok

### lesson→graph 桥接断裂

**症状**: `mcp_graphify_graph_search("教训主题")` 找不到教训条目，但 `~/.hermes/lessons/*.md` 文件中教训存在。

**根因**: `~/.hermes/scripts/lesson_graph_bridge.py` 中 `GRAPHIFY_BIN = None`——找不到 `graphify` CLI 路径。教训系统纯文本运行，从未桥接到图谱。

**验证**:
```bash
python3 -c "from scripts.lesson_graph_bridge import GRAPHIFY_BIN; print(GRAPHIFY_BIN)"
# 输出 None → 断裂
```

**影响**: graph_search 查不到教训内容，跨域教训无法通过图谱被推理发现。

**修复**: 将 lesson_graph_bridge 从 CLI 调用改为 MCP Python API 调用（直写 graph.json），或通过 `/graphify add` 指令逐条添加。

### 命名空间隔离 (brain:: vs .hermes::)

**症状**: `graph_search("数据铁律")` 找到节点，但 `graph_find_path(brain::节点, .hermes::节点)` 返回 "No path"。同一概念在两个空间各自存在但零桥接。

**根因**: graphify-daily cron 爬取 `~/brain/soul/` 生成 `brain::` 节点，另一次爬取对 `~/.hermes/profiles/` 生成 `.hermes::` 节点。两个命名空间独立存储，无合并策略。

**快速诊断**:
```bash
# 比较两个空间的域节点边数
graphify explain ".hermes::hermes_writing-domain"  # edges=1 孤岛
graphify explain "brain::brain_writing_domain"      # edges=22 丰富
```

**影响**: 跨命名空间图遍历(社区检测/路径查找)全部失效，推理能力受限。

**修复**: 在 graph.json 合并时对跨命名空间同名概念自动建立 `equivalent_to` 边。短期可手动桥接。
