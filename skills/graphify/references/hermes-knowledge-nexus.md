# Hermes 知识串联架构 (Knowledge Nexus)

会话日期: 2026-05-03 | 最后更新: 2026-05-06 | 状态: 已实现

## 五组件

| 组件 | 定位 | 路径 |
|------|------|------|
| GBrain | 关键词全文索引，即时搜索 | ~/brain/ → CLI: gbrain search/get/put; cron: 每6h sync |
| Graphify | LLM 语义知识图谱，社区聚类 | ~/.hermes/skills/graphify/; cron: 周一03:00 五合一 |
| Wiki | MECE 知识库，Git 版控持久化 | ~/brain/ (soul/ + agent/learnings/) |
| Hindsight | LLM 驱动记忆系统（local_embedded） | 本地安装: /home/pebynn/hindsight/; deepseek-v4-flash |
| Memory | Hermes 内置记忆工具，跨会话注入 | memory tool (hindsight 提供语义反思层) |
| Superpowers docs | 设计文档/计划知识源 | ~/docs/superpowers/specs/ + plans/; gbrain+graphify 双索引 [2026-05-07] |

## 串联架构

```
会话 ←→ Memory(hindsight)
  │ 6类知识归档(delegate成功+纠错+配置+死路+坑位+系统)
  ▼
Wiki(~brain/) ←── Graphify 周报 → see-also回写 → cross-refs.md
  │                    │
  ├── GBrain管理        ├── 周一03:00 cron (四合一)
  ├── gbrain-sync 6h    │
  │                    ▼
  ▼              Graphify 图遍历
GBrain keyword ─── 双路检索并行 ──→ 完整上下文 → delegate
  │
  └── 主 SOUL.md context-assemble 硬约束
      (gbrain search + mcp_graphify.graph_search 并列)
```

## 关键实现

### 1. 四张图谱（单 cron 四合一 → 五合一）

| 图谱 | 路径 | 包含于 cron |
|------|------|------|
| wiki 知识图 | ~/brain/graphify-out/ | 周一 03:00 (e1917ae814df) |
| profiles 域能力图 | ~/.hermes/profiles/graphify-out/ | 同上，顺序执行 |
| skills 80+技能依赖图 | ~/.hermes/skills/graphify-out/ | 同上，顺序执行 |
| Superpowers 设计文档 | ~/docs/superpowers/graphify-out/ | 同上，顺序执行 [2026-05-07 新增] |

Cron 完成后追加：merge-graphs 五合一 + cluster-only + see-also 回写 + cross-refs.md 更新 + memory-summary-latest.md。

### 2. 双路检索（硬约束）

主 SOUL.md 指令流水线 context-assemble 步骤强制执行：
```
├─ terminal: gbrain search "<关键词>" → 查 wiki 全文索引
├─ mcp_graphify.graph_search: 查知识图谱中相关节点
└─ 双路检索结果 + session + skill → 组装为 enriched_context
```

- GBrain: 关键词 → 命中文档（what）
- Graphify: 图遍历 → 命中关系路径（how）
- P0/P1 任务必执行，P2 跳过 assemble 但建议轻量检索

### 3. see-also 反向链接

cron 跑完后从 GRAPH_REPORT 提取 Surprising Connections（INFERRED 边），在两端的 wiki 页面底部追加 `## See Also` 交叉链接。下次 gbrain search 直接命中。

### 4. 图谱退化告警

每周 cron 对比两次统计，写入 ~/brain/graphify-out/ALERT.md：
- 节点/边下降 10%+ → critical
- God Node 出榜 → warning
- 新增孤立社区 → warning

会话启动时自动读取并汇报。

### 5. 知识归档 (archive_learning.py)

覆盖 6 类知识，写入 ~/brain/agent/learnings/YYYY-MM-DD-topic.md：
- `bugfix` — delegate 成功后的 bug 修复/验证结论
- `pattern` — 新模式/可复用流程
- `correction` — 用户纠错/偏好变更（最重要的信号）
- `config` — 配置决策及其理由
- `deadend` — 已确认不可行的方案标记
- `tool_pitfall` — 工具踩坑/环境限制

脚本: ~/scripts/archive_learning.py (170行)
用法: `python3 ~/scripts/archive_learning.py --topic "xx" --summary "xx" --type deadend --source "file.py" --tags "pdd,api"`

写入后自动触发 gbrain-sync 索引。批量抽取用 execute_code 批处理。

### 6. 技能同步 (skill-learnings-sync.py)

每日 04:00 cron (498c8bdd7715) 扫描 agent 自建技能变更，写摘要到 ~/brain/agent/learnings/skill-sync-YYYY-MM-DD.md。

脚本: ~/.hermes/scripts/skill-learnings-sync.py

### 7. 跨图引用索引 (cross-refs.md)

~/brain/cross-refs.md — 三张独立图谱的统一交叉引用：Wiki 节点 ↔ Skills 名称 ↔ Profiles 图节点。由 graphify weekly cron 的 see-also 步骤自动更新。

### 8. memory-summary 注入

### 6. memory-summary 注入

每次 graphify cron 写完 memory-summary-latest.md。主 SOUL.md "会话启动检查"段：每次对话开头自动读取，注入图谱摘要到后续任务理解。

## Token 开销特征

- 写路径（花 LLM token）：cron graphify / Hindsight reflect
- 读路径（零 token）：gbrain search(PG索引) / graphify query(NetworkX) / archive_learning.py(stdlib)
- 月增量：~30K tokens（graphify weekly semantic extraction）

## 已知局限

1. GBrain 不支持语义/跨语言搜索。补救：Graphify 社区聚类 = 语义近似分组，同社区节点即近邻。
2. 跨图边已实现 [2026-05-07]：merge-graphs 合并后可通过 execute_code 追加交叉引用边（如 superpowers_integration → hermes_agent）。cross-refs.md 保留作补充索引。
3. Hindsight 错误日志易误判——旧 gateway 实例的 `ModuleNotFoundError` 残留，需检查当前 gateway venv (`~/.hermes/hermes-agent/venv/bin/python -c "import hindsight"`) 而非日志。
4. archive 覆盖仍依赖手动触发——只有 skill-learnings-sync 有 cron；主代理需在 delegate 成功/用户纠错/配置变更时主动调用 `archive_learning.py`。
5. MCP server 缓存：graph.json 修改后需重启 session 才能被 MCP 读到。验证用 `graphify path` CLI 直读文件。
