# 域工具集完整性审计清单

> 来源：2026-05-01 全域工具集审计（ec/code/ops/research 四域 + 主代理）

## 核心问题

域 SOUL.md 的「配合技能」节列出了技能，但「可用工具集」节缺少 `skills` 工具 → 域长无法实际加载任何技能。**技能列表沦为装饰品。**

## 审计步骤

### 1. 读域 SOUL.md，提取三列数据

```
列A — 声明的 toolsets（可用工具集节）
列B — 引用的配合技能列表（配合技能节）
列C — 技能内部声明的 allowed-tools（每个 SKILL.md 的 YAML frontmatter）
```

### 2. 交叉校验

| 检查 | 方法 | 典型发现 |
|:-----|:-----|:--------|
| B∩A | 域有技能列表但 toolsets 无 `skills` | **所有域都是这个情况** |
| C⊆A | 每个技能的 allowed-tools 是域 toolsets 的子集 | 技能需要 browser 但域无 browser |
| 脚本可运行性 | 域工作流提到脚本但无 `terminal` | research-domain 缺 terminal |

### 3. 三类常见缺口

| 缺口 | 原因 | 影响 |
|:-----|:-----|:-----|
| 缺 `skills` | 域声明时遗漏，或认为 MCP 继承机制会覆盖 | 域长无法加载自身技能库，决策无知识支撑 |
| 缺 `terminal` | 域定位为"纯分析"但实际需要跑脚本 | 工作流中脚本（如 collect_hot_words.py）无法执行 |
| 缺 `search` | 忽略 session_search 的价值 | 无法回溯历史会话中的运营数据和决策 |

### 4. 主代理自审

主代理的「工具使用分层」表（🟢始终可用）应包含所有实际使用的工具。常见遗漏：

- `search_files` — grep/查找文件，极高频率
- `send_message` — 微信推送
- `process` — 后台进程管理
- `skills_list` — 列出技能（不同于 skill_view）
- `patch` — 配置编辑（🟡层已覆盖但🟢应明确"

### 5. 修复模板

```markdown
## 可用工具集
`toolsets: ['terminal', 'file', 'web', 'skills', 'search']`
- terminal — ...
- file — ...
- web — ...
- skills — 加载自身N个技能做决策
- search — session_search 回溯历史
```

## 已知所有域的共同缺口（2026-05-01）

| 域 | 缺 skills | 缺 terminal | 缺 search |
|:--|:--------:|:----------:|:--------:|
| ec-domain | ✅ | — | ✅ |
| code-domain | ✅ | — | ✅ |
| ops-domain | ✅ | — | ✅ |
| research-domain | ✅ | ✅ | — |
| finance-domain | — | — | — |

> finance-domain 是唯一在创建时就配齐 `skills` + `search` 的域，其余4域均为事后修复。

## config.yaml 深度检查项

审计域 config.yaml 时额外检查：

### delegation 参数完整性
```yaml
delegation:
  max_spawn_depth: N     # 必须 >= 域最坏调用链深度
  max_concurrent_children: N
  orchestrator_enabled: true/false
```

### spawn_depth 基准（2026-05-01 调整后）
| 域 | depth | 理由 |
|:--|:----:|:-----|
| 主代理 | 6 | 覆盖 `主→ec→sourcing→research→search→extract` 六层链 |
| ec-domain | 4 | 内部三阶段 (sourcing/listing/fulfillment) 各可再派一层 |
| code-domain | 3 | 写脚本时可拆测试子代理 |
| finance-domain | 2 | 量化分析可拆并行计算 |
| ops-domain | 1 | 不自派子代理 |
| research-domain | 1 | 由总指挥直派 |

### orchestrator_enabled 判断
- 域 SOUL.md 引用了子代理 skill → 必须 true
- 域的配合技能中包含 `profile-*-agent` → 必须 true
- 域纯粹执行/分析不拆任务 → false 可接受
