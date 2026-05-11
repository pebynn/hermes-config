---
allowed-tools:
- read_file
- patch
- write_file
- terminal
- delegate_task
- cronjob
- skills_list
- skill_view
author: unknown
description: 子代理域能力升级 — 将域从"被动脚本执行器"升级到"真正的领域专家"：审计→写脚本→配cron→升级模型/工具→改SOUL.md沟通风格为叙事报告
execution: manual
name: domain-capability-upgrade
trigger:
- user says "X domain doesn't deserve the title of Y"
- user says "check remaining domains against the same standard"
- user acknowledges a domain needs proactive data analysis, not just passive script
  execution
- after a domain capability upgrade succeeds, other domains need the same treatment
version: 1.0.0
---

# 子代理域能力升级

## 类定义

将一个 Hermes 子代理域从"接到命令执行脚本"升级到"真正的领域专家"的标准流程。

升级标准对照（以 finance-domain 为参照）：
1. ✅ 综合诊断/分析脚本 — 领域核心数据能一键采集
2. ✅ 日报/复盘脚本 — 自动出叙事报告
3. ✅ 模型升级 — deepseek-v4-pro（若适用）
4. ✅ 工具升级 — 加 browser/web_search 补充信息
5. ✅ 沟通风格 — 从表格升级为叙事报告格式
6. ✅ cron 定时推送 — 自动化日报推微信
7. ✅ 配合技能 — 引用相关 skill 增强能力

## 步骤

### 第1步：审计当前状态

```bash
# 读目标域的 SOUL.md
cat ~/.hermes/profiles/<domain>/SOUL.md

# 看 config.yaml 模型配置
cat ~/.hermes/profiles/<domain>/config.yaml

# 看有什么脚本
ls ~/.hermes/skills/*/<domain-relevant>/
```

对照 7 项标准逐项打勾，标识差距。

> **数据密集型域（如 finance-domain）扩展审计**：若域管理自己的数据存储（parquet缓存/MySQL/cron管线），参考 `hermes-config-audit` skill 的 `references/data-domain-audit.md` 执行完整资产审计，包括：缓存-vs-数据库一致性、API源矩阵、cron到数据馈送映射、脚本冗余检测。

### 第2步：写核心分析脚本

分析该域的核心工作流：数据从哪里来？输出什么？

对于每个域：
| 域 | 核心数据源 | 脚本模式 | 输出格式 |
|:---|:----------|:---------|:---------|
| finance-domain | akshare 金融数据 | comprehensive_analysis.py | JSON → 叙事报告 |
| ec-domain | PDD本地运营文件 | daily_ops_report.py | JSON → 叙事报告 |
| ops-domain | 系统状态（df/ps/docker） | system_health_check.py | JSON → 异常告警 |
| research-domain | web_search 结果 | — | 直接走 deep-research skill |

用 code-domain delegate_task 写脚本，用 deepseek-v4-flash（快），告诉子代理"一次写完不测试"。

### 第3步：配 cron 定时推送

创建 cron job：
```bash
cronjob action=create name="<域>日报" schedule="0 21 * * 1-5" \
  deliver="weixin:..." \
  prompt="执行脚本→读数据→写叙事报告→推微信"
```

交付格式规则：
- 复盘/日报类 → 全文作为消息文本推送（不用文件）
- 策略信号类 → .txt 文件 MEDIA 推送
- 检查: cron.toolsets 要包含子代理需要的工具集

### 第4步：升级模型+工具

在 config.yaml 中配置（注意 delegation bug — profile 配置不生效，需 delegate_task 时手动传 model）：

```yaml
# ~/.hermes/profiles/<domain>/config.yaml
delegation:
  model: deepseek-v4-pro  # 不会自动生效，仅在 SOUL.md 标注提醒
```

所以升级方式是在 SOUL.md 的"可用工具集"中标明：
```
调用此代理时必须传入 toolsets：`['terminal', 'file', 'web', 'browser', 'skills']` 且传 `model="deepseek-v4-pro"`
```

⚠️ **工具集审计**：升级后必须检查域声明的 toolsets 是否覆盖所有配合技能的需求。最常见遗漏是 `skills` — 所有域的「配合技能」节都列了技能，但 toolsets 常缺 `skills`。完整审计方法论见 `references/toolsets-audit-checklist.md`。

同时更新主 SOUL.md 的"可调度资源"表，标注 model+toolsets。

### 第5步：改 SOUL.md 沟通风格

从纯表格升级为叙事报告格式。模板：

```
## 沟通风格

- [域核心报告]用叙事报告：[列出报告包含哪些板块]
- 每个结论附带数据支撑
- [问题类型]标记紧急度（高/中/低）
- 给出具体可操作的建议
- 用表格做辅助对比，核心判断用文字阐述
```

同时更新"配合技能"引用：
- 看有什么 skill 可以增强该域的能力
- 新加的 skill 记得引用进来

### 第6步：更新主 SOUL.md

在"可调度资源"表里更新该域的行：
- 职责描述加新能力
- 触发条件标注 model + toolsets

### 第7步：测试跑一次

手动触发 cron 或用 delegate_task 跑一次完整流程，验证：
- 数据采集是否正常
- 报告格式是否符合预期
- WeChat 推送是否成功

## 已应用到此流程的域

| 域 | 状态 | 日期 | 升级内容 |
|:---|:-----|:-----|:---------|
| finance-domain | ✅ 完成 | 2026-04-29 | comprehensive_analysis.py + daily_market_review.py + pro+browser + 叙事报告 + 21:00市场复盘cron |
| ec-domain | ✅ 完成 | 2026-04-29 | daily_ops_report.py + sales_forecast.py + pdd_data_sync.py + 21:00运营日报cron + 叙事报告格式 |
| research-domain | ✅ 完成 | 2026-04-29 | deep-research 安装+知识库初始化 + profile-research-agent 创建 + 选品周报cron(周一10:00) |
| ops-domain | ✅ 完成 | 2026-04-29 | system_health_check.py + system_backup.py + 08:00巡检cron + SOUL.md核心能力升级 |
| code-domain | ✅ 完成 | 2026-04-29 | project_scaffold.py(全栈/CLI/数据三模板) + browser工具 + SOUL.md核心能力升级 |

## 进阶：Kanban架构全域升级（Kanban-Era Mass Domain Upgrade）

当架构从 delegate_task 切换到 kanban worker 后，需要对所有域进行一次系统性再审计和升级。本章涵盖该场景下的独特模式。

### 适用条件
- 架构切换后首次全域审计（delegate→kanban、单体→多worker等）
- 多个worker存在共性问题（如都缺少startup protocol）
- 需要通过调研→设计→实施三阶段完成能力跃迁

### 五阶段流程

```
Phase 1: 摸底（总指挥）
  cron list → profile config扫描 → 知识图谱统计 → 确定各worker当前状态

Phase 2: 并行深度调研（deep-research × N方向）
  功能性、发展方向、延展能力三个维度，覆盖所有worker域
  输出：行业基准（生产中什么模式存活）+ 各域gap矩阵

Phase 3: 批量加固（直接执行，L1）
  - 知识注入协议：批量patch所有worker SOUL.md，注入startup protocol
    （graph_search → lessons加载 → SOUL.md自检）
  - 工具脚本：创建辅助脚本（如 kanban_failure_collector.py）
  - cron升级：更新error-learner等cron覆盖kanban事件

Phase 4: 域升级设计（kanban并行派发）
  为每个需升级的域创建kanban任务：
  - research-domain调研 → code-domain实施（如EC架构升级）
  - 域内专家自行设计（如finance pipeline化）
  - ops-domain实施基础设施（如research→graphify管道）

Phase 5: 汇总收敛（cron自动或总指挥手动）
  所有kanban任务完成后汇总方案 → 投递通知
```

### 批量SOUL.md注入模式

当需要对所有worker统一注入启动协议、数据契约声明等时：

```python
# 模式：用execute_code并行patch，一个脚本覆盖所有worker
profiles = {"finance-domain": {"anchor": "## 核心能力", ...}, ...}
for name, cfg in profiles.items():
    content = read_file(cfg["path"])
    if "Startup Protocol" not in content:
        patch(path=cfg["path"], old_string=cfg["anchor"],
              new_string=startup_block + "\n" + cfg["anchor"])
```

关键：找一个每个SOUL.md都有且位置合适的anchor行（如`## 核心能力`），在它前面插入新内容。

### Skill Gap分析模式

评估每个worker是否有足够的skill支撑其核心能力：

| Worker | 检查方法 | 典型gap |
|:--|:--|:--|
| reviewer | 搜索skills list中有审核相关skill | 常有gap——审核域常被忽略 |
| writer | 搜索SEO、内容策略相关skill | 社区skill有安全风险，用内置指令替代 |
| code | 检查superpowers链完整性 | `code-review` vs `requesting-code-review`命名不一致 |
| ops | 检查自愈能力skill | 缺少AIOps级自动化 |

社区skill安装原则：贵精不贵多。安全扫描block的坚决不装。能用内置指令替代的不装外部skill。

### 模型切换——解决worker超时

kanban worker频繁reclaim → 检查模型是否适合该域：

| 域 | 典型问题 | 解决方案 |
|:--|:--|:--|
| code-domain | glm-5.1启速慢，940s超时 | 换deepseek-v4-pro |
| 高频flash worker | flash模型推理慢 | 换pro或调低复杂度 |

### Superpowers合规——Kanban Worker的工作流跳过问题

详见 `kanban-worker` skill的pitfalls。核心：worker被reclaim后急于完成，跳过自己的标准工作流。修复：SOUL.md加7步自检清单+强制产物要求。

## 域创建和重定向（Domain Creation & Redirect）

标准升级流程处理的是**现有域的能力增强**。本节涵盖域的**生命周期前端操作**：从零创建和重定向。

### 从零创建新域（Research-Driven Domain Creation）

当需要为全新业务领域创建域代理时，先用深度研究确认方向，再落地配置文件。

```
用户需求 → task-clarify → research-domain 深度调研 → 读4产出文件 → 创建域 → 注册
```

#### 细分步骤

**Phase 0: 需求澄清**
1. 跑 task-clarify.py 确认 domain/priority/constraints/expected_output
2. 确认是否涉及新领域知识（是 → 必须调研；否 → 跳过调研）

**Phase 1: 研究驱动（若涉及新领域）**
1. 加载 deep-research skill → delegate research-domain 做9维度研究
2. 读 executive-summary.md — 提取域的核心定位（150字以内）
3. 读 deep-dive.md — 提取技术选型、工具链对比、免费替代品
4. 读 key-players.md — 标注可用的开源工具/API/关键玩家
5. 读 open-questions.md — 标注已知风险（如"无官方API"）
6. 更新 knowledge/concepts.md 和 data-points.md

**Phase 2: 创建域目录**
```bash
mkdir -p ~/.hermes/profiles/<domain>/skills
mkdir -p ~/<domain-data>/{topics,drafts,publish-logs}  # 按需
```

**Phase 3: 编写域核心文件**

参考模板 `templates/domain-profile.template.md` 完成以下文件。

SOUL.md 模板骨架：
```yaml
---
name: <domain-name>
description: <一句话定位，从executive-summary提取>
version: 1.0.0
---
# <域中文名>

域定位：<完整描述>

## 核心职责
1. <职责1>
2. <职责2>
...

## 工具链（免费优先）
| 工具 | 功能 | 成本 | 使用方式 |

## 工作流协议
### 输入阶段
### 处理阶段
### 输出阶段

## 输出规范
### 每日产出

## 约束与红线
### 平台合规
### 质量标准
### 域边界
```

config.yaml 骨架：
```yaml
model:
  provider: deepseek
  model: deepseek-v4-flash
  temperature: 0.8

enabled_toolsets:
  - terminal
  - file
  - web

delegation:
  default_model: deepseek-v4-flash
  max_spawn_depth: 2
  timeout: 300

# 域特定配置
# <domain-specific config keys>

tracking:
  output_dir: ~/<domain-data>
  log_level: INFO
```

**Phase 4: 创建子技能**
1. 分析工作流 → 拆分为2-4个独立环节
2. 为每个环节创建技能目录 + SKILL.md
3. 技能命名规则：`<domain>-<action>-<entity>` 如 `a-share-data-collector`
4. 每个SKILL.md包含：触发条件、执行流程、工具链、输出规范、错误处理

**Phase 5: 注册到主SOUL.md**
```markdown
| <domain> | <一句话职责，含关键环节> |
```

**Phase 6: 测试**
1. 运行 start.sh 检查所有配置
2. 手动触发一个完整流程验证
3. 检查输出文件是否按预期生成

#### 参考案例：writing-domain（A股每日复盘） — 完整案例含C级升级

创建→重定向→C级升级的完整过程见 `references/a-share-daily-review-pipeline.md`。核心决策点：
- 从 research-domain 的深度调研输出（4文件）提取公众号写作域设计
- 用户反馈"方向调整为A股每日复盘" → 触发**域重定向**操作（见下方）
- 复用现有 ~/quant/ 管线（signal_engine、daily_signal_report、AKShare）

### 域变更/重定向（Domain Repurposing）

场景：域名不符合新定位，或方向需要重新聚焦（如 wechat-writing-domain → writing-domain，方向从通用公众写作改为A股复盘）

#### 变更清单

| 序号 | 操作 | 文件/位置 | 关键点 |
|:----:|:-----|:----------|:-------|
| 1 | 重命名域目录 | `mv ~/.hermes/profiles/<旧名> ~/.hermes/profiles/<新名>` | 不保留旧目录 |
| 2 | 更新主SOUL.md | "可调度资源"表 | 域名字段+描述 |
| 3 | 更新域SOUL.md | name + 描述 + 核心职责 + 工具链 + 工作流 | 名称frontmatter必须一致 |
| 4 | 更新config.yaml | 数据目录、模型配置、域特定参数 | 注意数据目录路径变更 |
| 5 | 重建子技能 | 删除旧技能目录 → 创建新技能 | 技能名应与新方向一致 |
| 6 | 更新README/start.sh | 使用指南 | 反映新域定位 |
| 7 | 清理旧数据目录 | 旧数据存档或合并 | 数据目录与域名解耦 |
| 8 | 最终验证 | 运行 start.sh → 确认 ✅ 就绪 | |

#### 注意事项

- **技能命名解耦**：技能名不应包含域名前缀。如 `writing-domain` 下的技能用 `a-share-data-collector` 而非 `writing-domain-data-collector`，因为技能描述的是能力而非所属域。域重命名时技能无需改名。
- **数据目录解耦**：数据路径应固定（如 `~/writing-data/`），不随域名变更。域名可改，数据积累不丢。
- **先建后删原则**：新技能创建并验证通过后，再删除旧技能目录。确保回滚路径。
- **config.yaml 中API凭证不变**：微信、AI等API凭证不随域名变更，无需重新配置。

## 进阶：研究驱动的域升级（Research-Driven Domain Upgrade）

当域的升级需求超越了"加点脚本、配个 cron"，需要系统性的领域知识注入时，使用这个三阶段模式。

### 适用条件
- 域需要理解全新的业务领域（非已有能力的增量优化）
- 升级涉及多个维度的知识空白（≥3个）
- 需要外部数据/研究来填充知识（非纯脚本能解决的）

### 三阶段流程

```
Phase 1: 研究（research-domain）
  识别知识空白 → 并行 deep-research（多个主题可用 tasks=[...] 并行）→ 输出四文件
  输出：~/research-skill-graph/projects/<topic>/ 下多个项目目录

Phase 2: 技能固化（目标域 + 研究输出）
  读研究成果 → 判断整合策略（新建技能 vs patch 已有技能）→ 创建/更新技能
  准则：可独立复用的知识领域 → 新建技能；互补增量的知识 → patch 已有技能

Phase 3: 整合收敛（目标域）
  更新域 SOUL.md 版本号 → 新增「认知升级」章节 → 更新技能引用清单
  目标：未来 delegate 该域时，它能自动加载新技能
```

### 参考案例：ec-domain v6.0→v8.0

| 阶段 | 内容 | 耗时 |
|:-----|:-----|:-----|
| Phase 1 | research-domain 4路并行研究（全站运营/店群/C2M/内容电商） | ~30min |
| Phase 2 | ec-domain 创建 5 个新技能 + patch 3 个已有技能 | ~7min |
| Phase 3 | SOUL.md v8.0 更新（新增认知升级章节 + 技能引用清单） | ~3min |

**关键发现**：ec-domain 原来的认知是"用淘宝思维做拼多多"（搜索SEO优先）。研究揭示拼多多本质是"活动驱动型"平台（40-50%流量来自活动资源位，搜索仅20-25%）。这是范式级认知跃迁，不靠研究无法自行发现。

### 与标准流程的关系

| 维度 | 标准流程（脚本驱动） | 研究驱动流程 |
|:-----|:-------------------|:------------|
| 输入 | 域自身数据源 | 外部研究（web_search+深度分析） |
| 核心产出 | 脚本 + cron | 技能（知识载体） + 认知升级 |
| 适用域 | finance-domain（数据驱动） | ec-domain（业务知识驱动） |
| 前置依赖 | 无（域自身就能做） | research-domain 必须先完成研究 |

## 进阶：跨域去重合并（Cross-Domain Dedup & Merge）

当系统出现多域膨胀（脚本/数据源/Skills 重复维护）时，用三阶段模式消除冗余。

适用场景：两域共享数据源/脚本/cron/技能，用户要求"降低系统臃肿度"。

详细方法论见 `references/cross-domain-merge.md` — 含双域并行审计→五维重叠分析→P0/P1/P2合并方案的完整流程、合并项模板、收益预估表。

实战案例：2026-05-07 finance-domain × writing-domain 跨域合并，产出 `/home/pebynn/quant/finance_writing_merge_plan_20260507.md`，发现：3对代码冗余、4类隐式重叠、Cron管线事实共享，预计净减少1800行(-9%)。

## 已知坑点

1. **delegation model 覆盖 bug** — profile config.yaml 设置不生效，必须在 delegate_task() 时手动传 model 参数
2. **ec-domain cron run** — cron 里的子代理不一定有 send_message 工具，需要确保 cron.toolsets 包含全
3. **脚本先写再测** — 脚本用 deepseek-v4-flash 写（快），写完我手动测，避免 pro 超时
4. **微信 iLink 会话 TTL** — 约1-2小时过期，过期导致推送失败。需要在推之前在微信上发消息刷新
5. **cron 错峰** — 多个 cron 在相同时间撞车时，错开5-30分钟（e.g., mid-cap 20:30, market-review 21:00, ops-report 21:00）
6. **子代理 send_message 权限** — delegate_task 的子代理默认没有 send_message 工具。需要推微信的任务应该由 cron prompt 直接写逻辑（cron 本身有 send_message 能力），或者保证 delegate_task 的 toolsets 包含 "send_message"
7. **称号对齐决策** — 审计后发现域配不上称号时，有两条路：(a)降称号，(b)升级能力补差距。用户倾向升级，没有降
8. **Phase 2 任务不要过大** — 整合多个研究项目到技能体系时，不要塞进一个 delegate_task（会 900s 超时）。先让子代理创建技能文件，SOUL.md 更新单独做。如果子代理超时，检查文件是否已部分写入——通常技能文件已创建成功，只是最后一步超时
9. **skills 工具集缺失** — 所有域的 SOUL.md「配合技能」节列出技能，但「可用工具集」常缺 `skills` → 域长无法加载任何技能。每次升级后必做工具集审计（`references/toolsets-audit-checklist.md`）
10. **技能命名解耦** — 技能名不应带域名前缀。`writing-domain` 下的技能用 `a-share-data-collector` 而非 `writing-domain-data-collector`。技能描述的是**能力**而非所属域，域重命名时技能无需改名。
11. **数据目录解耦** — 数据路径应固定（如 `~/writing-data/`），不随域名变更。域名可改，数据积累不丢。创建时直接选稳定路径。
12. **先建后删原则** — 域重定向时新技能创建并验证通过后，再删除旧技能目录。确保有回滚路径。
13. **config.yaml API凭证不变** — 微信、AI等API凭证绑定的是账号而非域名，域重命名时无需重新配置。
14. **域创建后的start.sh验证** — start.sh 应能独立检查域就绪状态（API配置 + 技能完整性），方便用户自检。
15. **API密钥泄露风险** — config.yaml 中不要放真实密钥，即使用 `sk-xxx...xxx` 部分脱敏也不行。一律用 `${ENV_VAR}` 引用，真实值放 `~/.hermes/.env`。升级任何域时都审计 config.yaml 中是否含明文密钥。
16. **cron环境无shell env** — cron 不走 login shell，`~/.hermes/.env` 不会自动加载。所有脚本必须在文件头解析 `.env` 作为兜底（`os.environ.get(key) or load_from_dotenv(key)`）。模式代码见 `references/a-share-daily-review-pipeline.md` 阶段4。

## 进阶：域模式化（Domain Moding — v1.1）

域代理从"单一全能模式"升级为"多模式可切换"：同一个域 agent，通过 context 注入 `mode=` 切换行为。

### 已模式化的域

| 域 | 受限模式 | 约束 | 用途 |
|:--|:--|:--|:--|
| research | researcher | 只采集+标注，不做分析/建议/结论 | Role链第1步 |
| writing | creator | 只写作，不自行采集数据 | Role链第2步 |
| finance | analyst | 只分析上游数据，不自行采集 | Role链第2步 |
| code | strict | 强制Superpowers 7步，不可跳过 | 生产代码 |

### 模式定义模板

在域 SOUL.md 顶部添加 `## 运行模式` 节，用表格对比 default vs constrained 的约束差异。主代理 delegate 时通过 context 注入 `mode=` 切换，不在 profile config 中硬编码。
