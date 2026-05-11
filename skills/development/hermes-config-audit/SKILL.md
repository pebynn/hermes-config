---
name: hermes-config-audit
description: Hermes 系统配置资产审计 — 验证所有配置文件的引用完整性、路径一致性、跨域交叉引用有效性和残留文件检测
version: 1.6.0
author: Hermes Community
allowed-tools:
  - read_file
  - search_files
  - skills_list
  - terminal
  - memory
  - cronjob
execution: manual
when-to-use: |-
  用户说：
  - "整体过一遍系统"
  - "审计/检查系统配置"
  - "检查配置文件有没有问题"
  - "检查技能是否有遗漏/分配是否完整"
  - "全面审查系统"
  - "system audit/health check"
  - "检查工具集/域配置/可用工具"
  - "所有config.yaml也过一遍"
  - After major restructuring (profile changes, skill bulk installs, config.yaml overhaul)
  - Periodic maintenance (every 2-3 months)
  - NOT for runtime health (use self-diagnosis) or code quality (use codebase-audit-and-repair)
---

# Hermes 系统配置资产审计

## 引用

本 skill 附带实战模式库 `references/audit-patterns.md`，记录在审计执行中发现的真实模式和技巧。执行审计前建议先阅读该文件。

新增：`references/weixin-delivery-error.md` — 微信推送 delivery error 的根因分析和修复路径。

新增：`references/data-domain-audit.md` — 数据密集型域（如 finance-domain）的扩展审计检查清单：parquet-vs-MySQL一致性、API源矩阵、cron到数据馈送映射、凭证过期检查。

## 审计范围

本 skill 覆盖以下 **静态配置** 的引用完整性检查：

| 层级 | 资产 | 检查项 |
|:----|:-----|:-------|
| 主配置 | `config.yaml` | 域引用完整性、external_dirs 有效性、delegation 段完整性、**api_key 是否使用 `$ENV_VAR` 而非硬编码** |
| Profile | 5域 `config.yaml` | 模型配置合理性、delegation 参数一致性 |
| 身份文件 | 5域 `SOUL.md` | 配合技能引用有效性、路径引用有效性、脚本清单与实际文件匹配 |
| 技能 | 所有 `SKILL.md` | linked_files 路径有效性、当安装的 skills_list 与磁盘一致性 |
| 脚本 | 各个管线脚本目录 | 目录完整性、路径 vs SOUL.md 声明一致性 |
| 定时任务 | `cronjob list` | 状态检查、last_run_at 与 last_delivery_error |
| CV 资产 | `.env` `auth.json` | API key 引用有效性、平台凭证残留 |

## 执行流程

### Phase 1: 采集基线

并行采集所有配置资产的元数据：

```
[总指挥]
  ├─ read_file config.yaml
  ├─ read_file .env
  ├─ read_file auth.json (credential_pool)
  ├─ read_file 5域 config.yaml
  ├─ read_file 5域 SOUL.md
  ├─ skills_list → skill_view 关键技能
  ├─ cronjob list
  ├─ search_files profiles/ skills/ 目录结构
  └─ terminal 检查关键脚本目录文件数量
```

### Phase 2: 交叉引用审计

逐项核对以下交叉引用：

**A. 配合技能 → 实际技能**
- 每个域 SOUL.md 的 `## 配合技能` 节中引用的所有 skill，检查 `skills_list` 中是否存在
- 标记缺失引用

**B. 脚本路径 → 实际文件**
- SOUL.md/SKILL.md 中声明脚本目录，检查 `search_files` 找到的实际文件数量是否匹配
- 标记 symlink 和文件数量差异

**C. 全局配置 → Profile 配置一致性**
- 对比 `config.yaml delegation` 段与各域 `config.yaml` 的 model/provider
- 发现预期偏差（如 code-domain 用 deepseek-v4-pro）和非预期偏差
- 记录 delegation 模型覆盖是否生效的已知 bug

**D. 文件唯一性检查**
- 检查同一组脚本是否出现在多个位置（如 `~/.hermes/skills/` 和 `~/.hermes/profiles/*/skills/` 下重复）
- 比较文件数量、版本号、最后修改时间
- 标记过期副本

**E. external_dirs 有效性**
- 检查 `config.yaml` 中 `skills.external_dirs` 配置的路径下是否有 SKILL.md
- 标记无可用技能的空引用目录

**F. API key 硬编码检查**
- 扫描 `config.yaml` 中所有 `api_key:` 行，检查值是否为 `$ENV_VAR` 语法
- **推荐使用 `mcp_security_auditor_scan_file`** 穿透遮盖扫描 `.env` 文件（`read_file` 会自动遮盖敏感值显示为 `***`，但审计器能检测到实际明文 sk-* 密钥）
- 检查 `.env` 文件权限是否为 `600`
- 硬编码的 `sk-*` 或其他裸字符串 key 需标记为 P1 问题
- 建议替换为 `$ENV_VAR` 引用（如 `$DEEPSEEK_API_KEY`、`$DASHSCOPE_API_KEY`）
- 注意区分：`providers.*.api_key: $VAR` 是安全的，`memory.api_key: sk-xxx` 和 `delegation.api_key: sk-xxx` 是风险点
- 同时检查 `.env` 文件中是否定义了对应的环境变量
- 使用 `stat -c '%a %U:%G' ~/.hermes/.env` 确认文件权限

**G. 工具集 vs 技能交叉检查**（v1.2 新增）
- 每个域 SOUL.md 的「配合技能」节列出技能，检查「可用工具集」是否包含 `skills`
- 域工作流提到脚本（如 research-domain 的 `collect_hot_words.py`），检查 toolsets 是否包含 `terminal`
- 域需要回溯历史（如运营日报对比），检查是否包含 `search`
- **已知模式**：几乎所有域的「配合技能」和「可用工具集」之间存在系统性脱节 — skills 工具集在所有域都缺失，直到显式审计
- 参考：`domain-capability-upgrade` skill 的 `references/toolsets-audit-checklist.md`

**H. spawn_depth 合理性验证**（v1.2 新增）
- 绘制最坏情况调用链：`主→域A(1)→子域B(2)→孙域C(3)→...`
- 主 config `delegation.max_spawn_depth` 必须 ≥ 最坏链长度
- 有 `orchestrator_enabled: true` 的域（ec/code/finance）需额外深度空间
- 没有 orchestrator 能力的域（ops/research）depth=1 通常足够
- 多域并行场景需更多余量（深度+2~3）
- **推荐配置**：主 depth=6, ec=4, code=3, finance=2, ops/research=1

**I. 主代理工具集完整性**（v1.2 新增）
- 检查主 SOUL.md「工具使用分层」🟢 行是否列出所有实际使用的工具
- 高频但常遗漏：`search_files`、`skills_list`、`send_message`、`process`
- 🔴 禁止行检查：`browser_*` 是否太宽泛？应精确列出禁止的 browser 子命令，🟢 中的 browser_snapshot/console/vision 作为例外
- `patch` 在 🟡 和 🟢 中的定位：🟡 约束限制，🟢 中 `patch(仅config)` 明确使用范围

**J. Gateway 状态分析**（v1.3 新增）
- 读取 `~/.hermes/gateway_state.json` 检查 `platforms` 段
- 注意：网关自动重启可能导致 state 文件被覆盖，如果文件不存在则跳过
- 分类标准：

| state | 含义 | 标记 |
|-------|------|------|
| `connected` | 正常 | 可通过 |
| `retrying` + 持续报错（>24h） | 凭证无效/缺失 | P2 — 建议修复或禁用 |
| `disconnected` + 无 error | 已关闭但配置存在 | P3 |
| 长期 `retrying` 不停止 | 底层重试循环影响网关性能 | P1 — 必须处理 |

- 典型发现：QQ Bot 持久 retrying 但 `.env` 中无 `QQ_*` 变量（凭证完全缺失）
- 操作建议：确认无对应环境变量后，从 gateway 平台列表中移除该平台

**K. 快照残留学徒检查**（v1.3 新增）
- 检查 `~/.hermes/state-snapshots/` 下是否有 `.env`、`config.yaml` 等文件的旧版本副本
- 使用 `find ~/.hermes -name '.env'` 检查所有子目录的暴露程度
- 权限为 `600` → 风险低但冗余；权限为 `644` 以上 → HIGH 安全风险（建议清理）

**L. MCP 连接串内嵌密码检查**（v1.3 新增）
- 扫描 `config.yaml` 中 `mcp_servers` 段的 `args` 字段，检查是否包含 `://.*:***@` 模式的连接字符串
- 即使显示为 `***`，实际文件中可能是明文密码
- 推荐改用环境变量：`mysql://user:${DB_PASSWORD}@host:port/db`

**M. profiles/ 目录污染检测**（v1.4 新增）
- 检查 `~/.hermes/profiles/` 下是否有非域代理目录：
  - `graphify-out/` — Graphify 对 profiles 建图时会在此生成 skills/ 子目录和 HTML/JSON 报告，污染域代理运行环境
  - `__pycache__/` — Python 缓存残留
  - 任何非 5 域 + 非必需的目录
- 命令：`ls ~/.hermes/profiles/ | grep -v -E '^(code-domain|ec-domain|ops-domain|research-domain|finance-domain)$'`
- 修复：删除污染目录（`rm -rf`），将 graphify 输出改到 `~/brain/graphify-out/` 而非 `~/.hermes/profiles/graphify-out/`

**N. orchestrator 能力与域职责匹配检查**（v1.4 新增，扩展 H）
- 检查各域 `config.yaml` 的 `orchestrator_enabled`：
  - ec-domain / code-domain / finance-domain — ✅ 可启用（域内有子代理编排）
  - ops-domain / research-domain — ❌ 不应启用（纯执行域，无需编排孙代理）
- 不匹配时：`orchestrator_enabled: false`，`spawn_depth: 1`

**O. Cron delivery error 模式检测**（v1.4 新增）

**P. 域实现完整性检查**（v1.5 新增）
- 检查每个域的技能是否有可执行实现：
  - 列出域 SOUL.md 中声明的所有技能 → 检查对应 `scripts/` 目录是否有 `.py` 文件
  - 标记"有 SKILL.md 但无脚本"技能（如 writing-domain 初始版本的 reviewer-writer/publisher）
  - 标记脚本中的数据公式错误（如涨跌幅用 `(close-open)/open` 而非 `(close-prev_close)/prev_close`）
- 检查域数据目录 `~/<domain>-data/` 的子目录是否有实际产出文件
  - 空 analysis/、空 drafts/ → 管线未实际运行
- 检查域 config.yaml 是否有硬编码密钥（除已知检查项 F 之外的域级文件）
- 检查 `cronjob list` 输出中 `last_delivery_error` 字段
- **已知模式**：`Weixin send failed: Timeout context manager should be used inside a task` — gateway 层 asyncio bug，非配置问题
- 此错误不影响任务执行（`last_status: ok`），仅影响微信推送
- 标记为 P2（需 gateway 升级/修复），非配置层面可修
- 详细排查见 `references/weixin-delivery-error.md`

### Phase 3: 归类基线变更

将发现的问题标记严重级别：

| 级别 | 定义 | 典型发现 |
|:----|:-----|:---------|
| P1 | 功能受损 | 代码副本不同步导致跑旧版、外部依赖看不到、引用失效导致子代理无法加载技能 |
| P2 | 配置不准确 | SOUL.md 未列全脚本、参数描述滞后、文件路径声明与实际情况不符 |
| P3 | 可优化 | 残留文件/目录、重复技能注册、备份文件未清理 |

### Phase 4: 输出审计报告

按此格式输出：

```
## 审计报告

### P1 — 立刻修
1) [问题描述] → [影响] → [修复方案]

### P2 — 建议修
1) [问题描述] → [影响] → [修复方案]

### P3 — 可做可不做
1) [问题描述]

### Cron 健康
| 任务名 | 状态 | last_run_at | last_error |

### 整体评分
| 维度 | 评分 |
|:----|:----:|
| 配置完整性 | X% |
| 引用一致性 | X% |
| 技能分配完整度 | X% |
```

## 快捷脚本

| 脚本 | 用途 |
|:--|:--|
| `scripts/profile-skill-dedup.py` | 检测/清理 profile 下与 master 重复的 skill 副本 |

```bash
# 检测（dry-run）
python3 ~/.hermes/skills/development/hermes-config-audit/scripts/profile-skill-dedup.py

# 删除纯重复副本
python3 ~/.hermes/skills/development/hermes-config-audit/scripts/profile-skill-dedup.py --delete
```

## 关键检查命令参考

```bash
# 检查技能总数
find ~/.hermes/skills -name 'SKILL.md' | wc -l

# 检查所有 profile config 的模型
grep 'model.default' ~/.hermes/profiles/*/config.yaml

# 检查 SOUL.md 是否缺失关键章节
for f in ~/.hermes/profiles/*/SOUL.md; do
  echo "--- $(basename $(dirname $f)) ---"
  grep '^## ' "$f"
done

# 检查 external_dirs 有效性
python3 -c "
import os, yaml
with open(os.path.expanduser('~/.hermes/config.yaml')) as f:
    cfg = yaml.safe_load(f)
for d in cfg.get('skills', {}).get('external_dirs', []):
    count = len([x for x in os.scandir(d) if x.name.endswith('.md')])
    print(f'{d}: {count} .md files')
"

# 检查脚本目录完整性
for dir in ~/.hermes/skills/development/*/scripts/; do
  count=$(ls "$dir"/*.py 2>/dev/null | wc -l)
  echo "$(basename $(dirname $dir)): $count scripts"
done
```

## 已知常见问题模式

| 模式 | 检测方法 | 修复 |
|:-----|:---------|:-----|
| profile 下技能副本过期 | `ls profiles/*/skills/*/*/` vs `ls skills/*/*/` 同名目录有差异 | 删 profile 下副本 |
| external_dirs 空洞 | 指向目录无 SKILL.md | 从 config.yaml 中移除 |
| 脚本散落未归入 skill | SOUL.md 声明 N 个脚本但实际目录只有 M 个 | 收集或更新文档 |
| 配合技能名拼写错误 | SOUL.md 引用的 skill 在 skills_list 中查不到 | 修正拼写或删除引用 |
| 已删除的 platform 残留凭证 | `.env` 中有 `QQ_*` 等变量但 config 无对应 platform_toolsets | 清理残留 |
| 死平台无限重试 | `gateway_state.json` 中平台 state=retrying 且 >24h | 禁用该平台或补全凭证 |
| 快照残留凭证 | `state-snapshots/<date>/.env` 存在 | 删除旧快照，保留最近1次 |
| MCP 连接串明文密码 | `config.yaml` 中 `mcp_servers.*.args` 含 `://user:***@` | 改为 `$ENV_VAR` 引用 |
| .env 文件权限不当 | `stat -c '%a' ~/.hermes/.env` 返回非 600 | `chmod 600 ~/.hermes/.env` |
| profiles/ graphify 污染 | `ls ~/.hermes/profiles/graphify-out/` 存在 | `rm -rf`，graphify 输出改到 ~/brain/ |
| profiles/ __pycache__ 残留 | `ls ~/.hermes/profiles/__pycache__/` 存在 | `rm -rf` |
| 执行域误开 orchestrator | ops/research 域 `orchestrator_enabled: true` | 改为 `false`，depth=1 |
| 微信 delivery 超时 | cron `last_delivery_error` 含 "Timeout context manager" | gateway 层 asyncio bug，需升级；见 references/ |
| 域技能无实现 | 域技能有 SKILL.md 但 scripts/ 目录为空 | 委托 code-domain 补全实现脚本 |
| 域数据采集公式错误 | 涨跌幅用 open 而非 prev_close 计算 | 修复 + 更新相关 skill 文档 |
| 域数据目录空洞 | 域数据目录存在但子目录为空（如 analysis/） | 检查管线是否实际产出数据 |
| Profile skills 大规模重复 | 5个profile各含56-92个skill副本，45个过期 | 删除profile下skills/，子代理从master加载 |
| 非标准 delegation 字段 | `delegation.default_model` 不是合法字段 | 改为标准 `model.default` 或确认版本支持 |
| 跨域段落逐字重复 | 同一规则在5个域SOUL.md中完全相同 | 只保留在主SOUL.md，域只留域特有规则 |
| 域SOUL.md结构缺失 | 缺少"任务前知识检索"/"核心脚本"/"协作规则"段 | 补全标准段 |

更多实战模式见 `references/audit-patterns.md`。

## 边界规则

- 不执行运行时测试（那是 self-diagnosis 的职责）
- 不修改源码逻辑（那是 codebase-audit-and-repair 的职责）
- 不调整 SOUL.md 内容质量（那是 soul-maintenance-audit 的职责）
- 仅做静态引用审计，发现不一致后建议修复方案
