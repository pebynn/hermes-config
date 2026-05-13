---
allowed-tools:
- terminal
- file
- delegate_task
- read_file
- session_search
author: unknown
description: 主动健康检查 — 验证所有能力域的可运行性和数据新鲜度
name: self-diagnosis
schedule: 0 5 * * 1
version: 1.11.0
---

# 自诊断健康检查

## 0. 全量迁移检查（新机器必做）

当 Hermes 从旧机器完整打包迁移到新机器时，必须执行完整的迁移检查清单。
详见 `references/migration-checklist.md`。

核心陷阱：
- 🔴 **systemd env** — gateway service 必须配置 EnvironmentFile + 显式 Environment= 才能让 MCP 读到 key
- 🔴 **venv pip binary 丢失** — 用 `python3 -m pip` 替代 `/venv/bin/pip`
- 🟡 **Gateway 重启卡 deactivating** — 等 90s，不行就 SIGKILL
- 🟡 **MySQL 无数据** — schema 迁移了，数据需回填

## 检查清单

### 1. 电商管线健康

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| 脚本存在 | `ls ~/.hermes/skills/development/ecommerce-auto-pipeline/scripts/*.py` | 4个脚本都存在 |
| Python 依赖 | `python -c "import playwright; import pandas; import openai"` | 不报错 |
| 17网可登录 | 尝试 playwright 打开 cs.17zwd.com | 页面加载成功 |
| 输出目录可写 | `touch ~/PDD/商品/.healthcheck` | 成功 |

### 2. 量化分析管线健康

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| 脚本存在 | `ls ~/.hermes/skills/development/finance-domain/scripts/*.py` | 至少6个脚本 |
| AKShare 可用 | `python -c "import akshare; print(akshare.__version__)"` | 返回版本号 |
| 数据源响应 | `python -c "import akshare; akshare.stock_zh_a_hist_tx('sz000001', '20260401', '20260428')"` | 返回数据（用腾讯源 hist_tx，东方财富 hist 可能连不上） |

### 3. Claude Code 源码完整性

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| 源码目录存在 | `ls ~/claude-code-source/src/` | main.tsx 等关键文件存在 |

### 4. 记忆健康

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| 记忆占用 | 检查 memory 响应中的 usage 百分比 | < 85% (留余量) |
| 记忆字符数 | 检查 memory 响应中的 chars 字段 | < 5100 (memory_char_limit=6000 时) |
| 条目数量 | 检查 memory 响应 entry_count | < 25（超过则需合并精简） |

⚠️ **Hindsight daemon broken** (2026-05-11): The hindsight daemon has never successfully started. `hindsight_recall/retain/reflect` MCP tools are non-functional. Built-in `memory` tool works independently. Skip hindsight-health-check cron (8832a6bdf66) — it checks a broken daemon. See `kanban-orchestrator` skill → `references/hindsight-audit.md`.

**记忆合并精简流程**（详见 `references/memory-consolidation.md`）：
- 删除纯历史记录（"已安装/已卸载/已删除于X日"）
- 合并同类：`memory action=replace content=NEW old_text=OLD` — **注意参数是 `content` 不是 `new_string`**
- 合并后检查重复残留 → `remove` 清理
- 更新过时引用（旧profile名/旧域架构描述）
- 目标：usage < 70%，entry_count ≤ 22
- 详细技巧见 `references/memory-consolidation.md`

### 5. 技能健康

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| 关键技能存在 | `ls ~/.hermes/skills/development/*/SKILL.md` | 所有域技能都存在 |
| 技能 frontmatter 完整 | 检查 yaml 格式 | 无语法错误 |
| 域SOUL.md 配合技能完整 | `grep '配合技能' ~/.hermes/profiles/*/SOOL.md` | 每个域应有此章节，所有引用的skill实际存在 |

### 6. 根定义文件（SOUL.md）新鲜度

SOUL.md 是总指挥的根定义文件，必须实时反映当前能力域。每次新增技能/子域后如果没更新它就是漂移。

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| 所有 profile-* 技能在 SOUL.md 有对应域 | grep profile- skills 列表 → 检查 SOUL.md 子代理表格 | 无遗漏 |
| 所有核心协议技能被引用 | batch-agent-processing / context-compression-protocol / reactive-skillify / subagent-delegation-protocol / self-diagnosis 应在 SOUL.md 中被提及 | 无遗漏 |
| SOUL.md 无过时引用 | SOUL.md 中列出的域应都有对应的 profile 技能存在 | 无悬挂引用 |
| background_jobs 目录存在 | `ls ~/.hermes/background_jobs/` | 目录可写 |

### 6.5. 会话目录健康（v1.6 新增 ⚠️ 高频遗漏）

详见 §23。

### 7. 子代理调度（delegation）健康

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| delegation 段存在 | `read_file ~/.hermes/config.yaml` 检查 delegation 段 | provider/base_url/model 已配置 |
| API key 在 config 中有效 | 检查 delegation.api_key | 不为空且格式正确（sk-开头或预期格式） |
| key 为空时检查 env var | `echo ${DASHSCOPE_API_KEY:0:10}` | 环境变量在当前进程中有值（重要：`.env` 文件存在 ≠ 变量已导出） |
| auth.json 凭证池状态 | `python3 -c "import json; d=json.load(open('~/.hermes/auth.json')); p=d['credential_pool'][PROVIDER][0]; print(f'status={p[\"last_status\"]} error={p.get(\"last_error_message\",\"\")[:60]}')"` | last_status = active 或 null，last_error_message 无 401 |
| base_url 一致性 | 对比 `grep base_url ~/.hermes/config.yaml \| grep 'delegation'` 与 `python3 -c "import json; print(json.load(open('~/.hermes/auth.json'))['credential_pool'][PROVIDER][0]['base_url'])"` | config 与 auth.json 的 base_url 必须完全一致 |
| 检查 profile 覆盖 | `grep api_key ~/.hermes/profiles/*/config.yaml 2>/dev/null \|\|echo '无profile覆盖'` | 无 profile 用空 api_key 覆盖主配置。local profile 如已删除则跳过检查 |
| provider override 实际测试 | 执行 `delegate_task(goal="ping", model=<MODEL>, provider=<ALT_PROVIDER>)` 观察是否仍走默认 provider | 若不尊重 override 参数（如传 deepseek 仍报 alibaba 401），说明 delegation 工具忽略 provider 参数 |
| 源文件完整 | `ls ~/.hermes/hermes-agent/tools/delegate_tool.py` | 文件存在 |

**故障自动诊断逻辑**（按优先级链排查）：

1. **base_url mismatch** — config 写 `dashscope.aliyuncs.com` 但 auth.json 是 `dashscope-intl.aliyuncs.com`（常见陷阱：国内版 vs 国际版 endpoint 不匹配导致凭证解析失败）
2. **env var 未导出** — 只在 `.env` 文件中有 key 但未 `source ~/.hermes/.env`，当前进程找不到环境变量 → 需要 `set -a; source ~/.hermes/.env; set +a`
3. **auth.json 凭证池耗尽** — last_status=exhausted, last_error_message 含 401 → 哪怕 config 中 api_key 已更新，凭证池仍用旧 key 拒绝请求。修复：重置 `last_status='active'; last_error_code=None`
4. **provider override 被忽略** — delegate_task 传入 `provider=zai, model=GLM-4.7` 但错误仍指向 alibaba → 当前 delegation 工具存在已知 bug：`_build_child_agent()` 的 override 参数永远不会被传入
   - 修复：临时把 api_key 直接写在 `delegation.api_key` 中（绕过凭证池）
   - 长期：需要改 Hermes 源码 `model_tools.py` + `tools/delegate_tool.py` 的 `DELEGATE_TASK_SCHEMA` 增加 model/provider 参数
5. **API key 真的过期** — 直 curl 测试确认：`curl -s PROVIDER_ENDPOINT -H "Authorization: Bearer $KEY" -d '{"model":"MODEL","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'` 返回 401 → 走 `api-key-rotation` skill 全量替换

**修复后的验证**：
```bash
# 验证 cred pool 状态
python3 -c "import json; d=json.load(open('/home/pebynn/.hermes/auth.json')); p=d['credential_pool']['alibaba'][0]; print(f'base_url: {p[\"base_url\"]} status: {p[\"last_status\"]}')"

# 测试 delegation
delegate_task(goal="只回复 ok", toolsets=[])
```

**MCP 热加载陷阱** ⚠️
- MCP server 是 gateway 的子进程，在 gateway 启动时 fork
- 修改 `mcp-*.py` 文件后 MCP server **不会**自动重载
- 即使 `systemctl restart gateway`，如果 gateway 崩溃后 systemd 快速重启（<1s），MCP 子进程可能复用旧代码
- **最可靠的方式**：先 `pkill -f mcp-<name>` 杀掉旧进程，再重启 gateway
- 验证：`grep GRAPH_PATH ~/.hermes/mcp-servers/mcp-graphify.py` 确认文件内容正确，然后重启后调用 MCP tool 测试

**服务启动排障节奏** ⚠️
- 容器启动卡住 → 先看日志（`docker logs <name> --tail 20`），找根因，**不要连续重试**
- 每次重试可能是同一个错误在循环，浪费时间且不产新信息
- 确认根因后给用户时间预期（"约需60秒"），再执行修复
- 修复后**一次验证**，失败就分析新症状，不反复重试

### 7.5. 系统重启 — Cron 脱靶检测（v1.7 新增）

**场景**：系统重启后，固定调度的 cron job（如 `0 8 * * *`）在宕机期间的任务不会被自动补跑。如果 uptime 较短且当前时间已过部分 cron 的调度窗口，这些 job 需要手动触发。

| 检查项 | 方法 | 通过条件 |
|:------|:-----|:---------|
| 系统已运行时间 | `uptime -s` 获取启动时间 | — |
| 今日已错过的调度窗口 | 对比 `uptime -s` 与所有 `schedule: "0 * * * *"` 的 cron job 的 **整点/半点** 窗口 | 启动时间之后的窗口无固定调度 job 被跳过 |
| 关键脱靶缺口 | 重点关注 08:00/08:05/09:00 等高频时段 | agenda-builder / morning-brief / ops-autopilot 等不应长时间未执行 |
| 触发补跑 | `cronjob action=run job_id=<ID>` 逐个触发 | 触发后 `next_run_at` 更新为当前时间 |
| 验证执行 | 检查 `agent.log` 中是否出现 `Running job '<name>' (ID: <ID>)` | 日志中出现对应条目 |

**修复流程**：
```bash
# 1. 检查重启时间
uptime -s    # e.g. 2026-05-08 08:56:41

# 2. 列出所有 cron job 找到可能的脱靶
cronjob list | grep -E 'schedule.*\*.*\*.*\*' | grep -E '"|name'

# 3. 对每个脱靶 job 手动触发
cronjob action=run job_id=<id>

# 4. 注意：cronjob action='run' 后不会立即执行
# 调度器有自己的轮询间隔，且如果有两个 mcp-hermes-cron.py 进程可能产生冲突
# 建议在触发后等待 30-60 秒检查 agent.log 确认
```

**陷阱** ⚠️：
- `cronjob action='run'` 只是排入队列，**不会立即执行**。调度器轮询间隔约 30-60 秒。
- 两个 mcp-hermes-cron.py 进程同时运行时可能互相干扰，导致触发的 job 未被执行。需确认 `ps aux | grep mcp-hermes-cron | wc -l` 为 1。
- `no_agent: true` 的脚本型 cron（如 agenda-builder）是独立进程，不生成 agent.log 的 "Running job" 条目，需通过输出去向（如 daily.md 是否更新）来判断执行结果。
- 补跑可能产生副作用（如 morning_brief 在 09:00 生成，但盘前数据可能已经过时）。对于 LLM cron，补跑时会收到当前时间的上下文，自动适配。

### 8. 定时任务健康

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| cronjob 列表 | `cronjob list` | 周度自优化任务存在且启用 |
| 微信投递限频 | `cronjob list` 检查 `last_delivery_error` 含 "rate limited" | 0 个 job 有此错误 |
| 时间窗口冲突 | 列出所有 `deliver: weixin:*` job，同小时 ≤ 1 个 | 无冲突 |
| 投递密度 | 工作日 weixin 投递总量 | ≤ 5 条/天，间隔 ≥ 2h |
| 时间冲突 | 检查同分钟多 cron → 应错开 ≥5min | 无精确冲突 |
| 30min拥堵 | ≥4 cron 在 30min 窗口内 → 应合并或分散 | 无拥堵 |

**微信投递限频修复**：
WeChat iLink 有严格频率限制。多个 job 在同一分钟投递触发 `ret=-2 rate limited`，即使跨时段也可能累积触发。

**限频诊断**（详见 `references/ilink-rate-limit-diagnosis.md`）：
- `errors.log` 中的 `[session_id]` 揭示哪个会话在消耗配额
- 旧 session 投递队列在 gateway 重启后仍会重试，每次重试刷新 iLink 冷却计时器
- iLink 冷却约 1h，冷却期内不要反复测试
- **关键陷阱**：清理 cron 后旧队列可能还在消耗配额，需等冷却周期过才能验证修复效果

**Cron 归并模式**（详见 `references/cron-merge-patterns.md`）：
- 早间归并：同时间段多任务合并为一个 prompt
- 晚间归并：同投递目标的多个 job 合并为一次 weixin 推送
- 周度归并：多个周度任务（如 graphify）合并到一个时间槽
- 降级投递：非紧急任务（watchdog/cost-report）weixin→local

```bash
# 密集时段 stagger 示例
cronjob action=update job_id=<id> schedule="5 21 * * 1-5"   # 原来 0 21
cronjob action=update job_id=<id> schedule="10 21 * * 1-5"  # 原来 0 21
```
长期方案：减少微信投递 job 数量，将非紧急报告改为 `deliver: local`。

### 9. Profile 层级与配置漂移检查

Hermes 配置有优先级链：domain profile > main config。**注意**：local profile 可能已被删除（推荐配置——统一走单一 config.yaml）。

**第一步：确认是否有 local profile**
```bash
ls ~/.hermes/profiles/local/ 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND"
```
- 如果 local profile **不存在**：跳过所有 local profile 检查项。配置直接走主 config.yaml，无覆盖风险。
- 如果 local profile **存在**：它覆盖主 config.yaml 的对应键，须逐项检查一致性。

**local profile 存在时的检查：**

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| local profile model.default | 对比 `~/.hermes/config.yaml` vs `~/.hermes/profiles/local/config.yaml` | 如果 local 用了不同模型（如 qwen2.5:1.5b），确认是用户有意为之 |
| 主 config 高优优化被覆盖 | 对比 personality / show_cost / web.backend / sessions.auto_prune / logging.max_size_mb / cron.max_parallel_jobs / memory_char_limit | local profile 不应保留旧默认值覆盖已优化的主配置 |
| local SOUL.md 架构一致性 | 对比 `~/.hermes/SOUL.md` (8域) vs `~/.hermes/profiles/local/SOUL.md` | local SOUL.md 应反映同样的 8 域架构，不应过时到旧版 2 域 |

**所有情况下都检查：**

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| 域代理 model 与 delegation 一致性 | 对比 `grep 'model.default' ~/.hermes/profiles/*/config.yaml` 与 `grep -A2 '^delegation:' ~/.hermes/config.yaml \\| grep 'model:'` | 所有域代理 model.default 应与 delegation.model 一致，除非用户特意指定了某个域用不同模型（如 code-domain 用 GLM-4.7）。不一致的域需要在 memory 中记录为"特意为之"的例外，否则视为配置漂移 |
| 域 SOUL.md 无矛盾参数 | 跨文件 grep 常用参数（如 `退货率`、`定价`、`倍率`） | 所有子代理对同一参数的定义应一致 |
| 域 SOUL.md toolsets 完整性 | `grep '可用工具集' ~/.hermes/profiles/*/SOUL.md` | 每个子代理 SOUL.md 应有 `可用工具集` 节，明确 delegate 时应传入的 toolsets |

**典型漂移模式**：
- local profile 存在且未同步 → 主 config 的优化被无声覆盖（最常见陷阱）
- 子代理 SOUL.md 描述跨平台能力但实际只配了单一数据源
- 子代理 SOUL.md 无 toolsets 声明 → delegate 时不传工具，子代理无法执行
- 域 SOUL.md 间参数矛盾（如旧 ec-pdd 退货率 18% vs ec-sourcing 25%，现已统一合并为 ec-domain）

### 10. 无用平台/服务检查

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| QQ Bot WebSocket 在线 | `grep 'QQBot.*Ready' ~/.hermes/logs/gateway.log \| tail -1` | 应有 `Ready, session_id=...` 记录，且时间戳在最近1小时内 |
| QQ Bot 无持续断线 | `grep 'QQBot.*WebSocket closed' ~/.hermes/logs/gateway.log \| tail -3` | 只有 `code=4009`(session超时)是正常的，不应有连续断线或 `code=1006` |
| **WeChat/iLink 已废弃待清理** | `ps aux | grep -iE 'ilink\|wechat' | grep -v grep` | 无进程运行 |
| 其他平台是否在空跑 | `grep 'ERROR.*adapter' ~/.hermes/logs/errors.log \| grep -v 'QQ Bot' \| head -10` | 无持续重试的平台连接错误 |
| 卸载遗留 | `which ollama` 或检查 docker 中无关镜像 | 已卸载的工具不应留下 process 或 binary |

**全平台清理**：不用的平台（如 telegram/discord/whatsapp/slack/signal/homeassistant）仍保留在 `platform_toolsets` 中，gateway 启动时会尝试初始化。检查：
```bash
grep -A15 'platform_toolsets' ~/.hermes/config.yaml | grep -v '^\s*#'
```
预期输出应只有 `cli:` 相关行。其他平台如果不需要，注释掉：
```yaml
# telegram:
# - hermes-telegram
```

同时检查 AWS Bedrock 是否启用（如果不用 AWS）：
```bash
grep -A2 'discovery' ~/.hermes/config.yaml
```
预期：`enabled: false`

**修复**：持续报错（如 QQ Bot 每5分钟重试）→ 需要两步全部执行：
1. 在 `~/.hermes/config.yaml` 的 `platform_toolsets.qqbot` 段注释掉（如有 local profile，同样注释）
2. 在 `.env` 中删除该平台的全部凭证变量（如 QQ_APP_ID、QQ_CLIENT_SECRET、QQ_ALLOW_ALL_USERS 等）
注意：只做一个不够——必须 config + .env 同步清除，gateway 重启后才停止重试。

### 11. Cron Scheduler 进程健康

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| gateway 服务运行 | `systemctl --user status hermes-gateway.service 2>&1 \\| grep 'active (running)'` | 服务应为 active (running) |
| cron ticker 日志 | `grep 'Cron ticker' ~/.hermes/logs/gateway.log \\| tail -3` | 应有 `Cron ticker started` 记录 |
| scheduler 进程存在 | `ps aux \\| grep 'gateway run' \\| grep -v grep` | 当前 gateway 进程在运行（cron 内嵌于 gateway） |
| last_run_at 不为 null | 检查 cronjob list 输出的 `last_run_at` | 对于已存在超过调度周期时间窗口的任务，不应全为 null |

**修复**：scheduler 进程不存在 → 重启 gateway (`systemctl --user restart hermes-gateway.service`) 后重新检查。如果仍然没有，检查 cron 目录完整性 (`ls ~/.hermes/cron/` 应有 jobs.json)。

### 12. Camofox 浏览器健康

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| Camofox 服务运行 | `curl -s http://localhost:9377/health` | 返回 `{"ok":true,"running":true}` |
| CDP URL 配置 | `grep cdp_url ~/.hermes/config.yaml` | `cdp_url: http://localhost:9377` |
| managed_persistence | `grep managed_persistence ~/.hermes/config.yaml` | `true` |
| systemd 服务 | `sudo systemctl is-active camofox.service` | `active` |
| 版本 | `curl -s http://localhost:9377/health \| python3 -c "import sys,json; print(json.load(sys.stdin)['version'])"` | 返回版本号 |

**修复**：服务未运行 → `sudo systemctl restart camofox.service`

**陷阱**：服务名是 `camofox` 不是 `camofox-browser`。`systemctl is-active camofox-browser` 返回 `inactive` 但服务实际在跑。
如果 Camofox 不再需要（已用 stealth-browser 替代），彻底停用：
```bash
sudo systemctl stop camofox.service
sudo systemctl disable camofox.service
```
systemd 的 Restart 策略会使 kill 进程无效——必须 disable 服务本身。

### 13. 网页搜索健康（web_search）

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| 配置的后端 | `grep -A1 'web:' ~/.hermes/config.yaml \| grep 'backend'` | `tavily`, `firecrawl`, `parallel`, `exa` 之一 |
| Tavily key 存在 | `grep TAVILY ~/.hermes/.env` | 行存在且非空 |
| Tavily key 可达 MCP server | `echo $TAVILY_API_KEY \| wc -c` | > 20（已导出为环境变量） |
| 实测通断 | `delegate_task(goal='用web_search搜test', toolsets=['web'])` 观察是否返回 401 | 不报 401 |

**关键陷阱**：`~/.hermes/.env` 中有 TAVILY_API_KEY ≠ MCP server 能读到。MCP server 是独立进程，在 gateway 启动时快照环境变量。修改 `.env` 后必须重启 gateway（`systemctl --user restart hermes-gateway.service`）才能让 MCP server 重新读取。`~/.zshrc` 中的 export 对新 shell 有效，但对已运行的 MCP server 进程无效。

**多条密钥更新路径**（按优先级）：
1. 写入 `~/.hermes/.env` + 重启 gateway（MCP server 重读）
2. 写入 `~/.zshrc`（新 shell 会话自动 export）
3. 终端内 `export TAVILY_API_KEY=...`（当前会话临时生效）

**故障链路**：Tavily 401 → 检查 `.env` 里 `TAVILY_API_KEY` → 如果过期需去 https://app.tavily.com/home 换新 → 写进 `.env` → **重启 gateway**。

### 13.5. 网页抓取工具链健康

检查渐进式抓取管线是否完整：

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| Jina Reader skill 存在 | `ls ~/.hermes/skills/research/jina-reader/SKILL.md` | 文件存在 |
| Crawl4AI skill 存在 | `ls ~/.hermes/skills/research/crawl4ai/SKILL.md` | 文件存在 |
| Crawl4AI pip 包 | `source ~/.hermes/hermes-agent/venv/bin/activate && python -c "import crawl4ai; print(crawl4ai.__version__)"` | 返回版本号 |
| Jina Reader API 可达 | `curl -s -o /dev/null -w '%{http_code}' 'https://r.jina.ai/https://example.com'` | 200 |

**修复**：Crawl4AI 未安装 → `pip install crawl4ai -i https://pypi.tuna.tsinghua.edu.cn/simple`

### 13.6. 技能生态健康

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| 技能总数 | `find ~/.hermes/skills -name 'SKILL.md' \| wc -l` | >= 50（合理范围 50-60） |
| 分类目录数量 | `ls -d ~/.hermes/skills/*/ \| wc -l` | 8-12 个活跃分类 |
| 过时技能 | 检查 `ec-domain` (已取代 `profile-ec-pdd-agent`/`profile-ec-sourcing-agent`/`profile-ec-fulfillment-agent`) 及已删除的 `profile-background-agent`/`profile-research-agent` 是否仍存在 | 应已删除或整合（ec已内部化） |
| 空分类目录 | `find ~/.hermes/skills -empty -type d` | 无 |
| 域 SOUL.md 技能引用 | 每个域 SOUL.md 的 `配合技能` 节与实际安装技能一致 | 无悬挂引用 |

**修复**：清理空目录 `find ~/.hermes/skills -empty -type d -delete`

### 15. 文档处理管线健康

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| Pandoc 可用 | `pandoc --version \| head -1` | 返回版本号 (>= 3.x) |
| Marker 可用 | `which marker_single && marker_single --help 2>&1 \| head -3` | 返回帮助信息 |
| Marker 模型已下载 | `ls ~/.cache/surya/ 2>/dev/null \| wc -l` | >= 1 (模型已缓存) |
| 管道联通 | `echo '# test' > /tmp/pipe_test.md && pandoc /tmp/pipe_test.md -o /tmp/pipe_test.pdf 2>&1` | 成功生成 PDF |

### 16. 语音识别工具健康

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| Whisper 可用 | `python3.12 -c "import whisper; print(whisper.__version__ if hasattr(whisper,'__version__') else 'ok')"` | 返回版本号 |
| Whisper 模型已下载 | `ls ~/.cache/whisper/` | tiny.pt 和 base.pt 存在 |
| FFmpeg 可用 | `ffmpeg -version \| head -1` | 返回版本号 |

### 17. Token追踪工具健康

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| Tokscale 可用 | `tokscale --version 2>&1 \| head -1` | 返回版本号 |
| Hermes 数据可读 | `tokscale --hermes --json 2>&1 \| head -5` | 返回 JSON 数据 |

### 18. 自进化工具健康

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| Self-evolution 代码存在 | `ls ~/.hermes/evolution/ 2>/dev/null \|\| echo 'N/A (may be in venv)'` | 路径存在或已迁移 |
| 包装脚本存在 | `which hermes-evolve` | 可执行 |
| dry-run 验证 | `HERMES_AGENT_REPO=/home/pebynn/.hermes hermes-evolve --skill finance-domain --dry-run 2>&1 \| grep 'DRY RUN'` | 返回 setup validated 信息 |
| Cron 任务存在 | `cronjob list 2>&1 \| grep '自我进化'` | 任务存在且启用 |
| **evo-autonomous-orchestrator 未暂停** (v1.11) | `cronjob list 2>&1 \| python3 -c "import sys,json; jobs=json.load(sys.stdin); evo=[j for j in jobs if 'evo-autonomous' in j.get('name','')]; print('PAUSED' if evo and not evo[0].get('enabled') else 'OK')"` | OK（自进化管线不能停） |
| compression 未复发 (v1.11) | `grep -A2 '^compression:' ~/.hermes/config.yaml \| grep enabled` | 输出必须是 `enabled: false` |
| model.default 非 reasoning 模型 (v1.11) | `grep -A1 '^model:' ~/.hermes/config.yaml \| grep default` | 应为 flash/chat 而非 pro（orchestrator 不需要 reasoning） |

### 19. 安全审计工具健康

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| Security-auditor skill 存在 | `ls ~/.hermes/skills/security/security-auditor/SKILL.md` | 文件存在 |

### 20. 大型无用文件检查

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| venv 体积 | `du -sh ~/.hermes/hermes-agent/venv/` | < 3GB（如果 > 5GB 含多余 GPU 包） |
| checkpoints 体积 | `ls -lh ~/.hermes/checkpoints/ | head -5` (不要用 `du -sh`，大目录会超时) | 保留 5-10 个快照为宜，>30 个需清理 |
| checkpoints 数量 | `ls ~/.hermes/checkpoints/ | wc -l` | < 20
| .env 行数 | `wc -l ~/.hermes/.env` | < 100 行（超过可能含有大量注释模板） |
| .env 活跃/注释比 | `grep -c '^[A-Z]' ~/.hermes/.env \|\| echo 0; grep -c '^#' ~/.hermes/.env \|\| echo 0` | 活跃变量应 > 注释行 / 3 |
| .env 中失效平台凭证 | `grep '^QQ_\|^QQBOT_\|^OLLAMA_' ~/.hermes/.env` | 已禁用/卸载的服务不应留凭证 |
| .env 无行号污染 | `head -5 ~/.hermes/.env \| od -c \| head -3` | 行首不应有 `N|` 前缀（数字+竖线） |

### 21. 系统结构健康（Structural Hygiene）

检查文件系统层面的杂乱和孤立文件——这些不会影响运行时功能，但会随时间累积造成混乱。

| 检查项 | 方法 | 通过条件 |
|:-------|:-----|:---------|
| 空 skill 目录 | `find ~/.hermes/skills -empty -type d` | 无（空目录无 SKILL.md 是残留） |
| `__pycache__` 残留 | `find ~/.hermes/skills -name __pycache__ -type d` | 无（Python 自动生成，定期清理） |
| 根目录孤立文件 | `find ~ -maxdepth 1 \( -name '*.py' -o -name '*.sh' -o -name 'package*' \)` | 无（脚本应归 ~/quant/，package 归项目） |
| Skill-repos 缓存 | `test -d ~/tools/skill-repos && echo exists || echo gone` | 如果技能已安装完毕应删除克隆缓存 |
| Shebang 一致性 | `head -1 ~/quant/*.py \| grep -v 'tools/quant_env'` | 所有量化脚本 shebang 应指向 `~/tools/quant_env/bin/python3` |
| 隐藏 AI 代理配置 | `du -sh ~/.agents/ ~/.augment/ 2>/dev/null \| cut -f1` | 已卸载的 IDE 插件不应留下 >100K 的配置目录 |
| Cron 推送状态 | 检查 `cronjob list` 中每个 job 的 `last_delivery_error` | 无持续报错（如 `platform 'weixin' not configured`） |

### 21.5. data_guard 管线门禁健康（v1.8 新增，v1.10 增强：分叉检测）

data_guard.py 是管线数据质量强制门禁，必须确认在岗且无代码分叉。

| 检查项 | 方法 | 通过条件 |
|:-------|:-----|:---------|
| data_guard.py 存在 | `test -f ~/writing-data/shared/data_guard.py` | 文件存在 |
| **代码分叉检测** | `diff ~/writing-data/shared/data_guard.py ~/writing-data/scripts/shared/data_guard.py 2>/dev/null || echo 'MISSING_COPY'` | 两份副本内容完全一致（或只有一份存在） |
| 字段映射完整性 | `python3 -c "exec(open(os.path.expanduser('~/writing-data/shared/data_guard.py')).read()); print(f'SINA_INDEX={len(SINA_INDEX)}, STOCK_SDK={len(STOCK_SDK)}')"` | 至少4个映射集已定义 |
| enforce_pipeline_gate 存在 | `grep -c 'def enforce_pipeline_gate' ~/writing-data/shared/data_guard.py` | 返回 1（不是 0） |
| drift检测 cron 存在 | `cronjob list 2>&1 \| grep 'data-guard-drift-detect'` | 任务存在且启用 |
| 管线集成点 | `grep -c 'data_guard' ~/writing-data/scripts/collect_data.py ~/writing-data/scripts/generate_charts.py ~/writing-data/scripts/generate_review.py ~/writing-data/scripts/weekly_summary.py ~/writing-data/scripts/publish_draft.py 2>/dev/null` | 至少5个脚本已集成 |
| audit_guard importable | `python3 -c "import sys; sys.path.insert(0,''); from audit_guard import audit_draft; print('ok')"` 2>&1 | 不报 ImportError |

**修复**：data_guard.py 缺失 → `cp ~/.hermes/skills/devops/data-accuracy-layer/scripts/data_guard.py ~/writing-data/shared/`。集成点缺失 → 参考 data-accuracy-layer skill 的 references/deploy-layout.md。

### 22. MCP Server 连通性（v1.4 新增）

MCP server 是独立进程，环境变量在 gateway 启动时快照。修改 `.env` 后不经重启不会生效。

| 检查项 | 方法 | 通过条件 |
|:------|:----|:--------|
| 逐个连通测试 | 对每个 MCP server 调用基础工具（如 `mcp_github_get_me`、`mcp_time_get_current_time`、`mcp_mysql_test_connection`） | 返回正常数据 |
| MySQL 浏览器面板 | `scripts/db_viewer.py` — 轻量 Web 数据库浏览器（http://localhost:8899），需 quant_env Python（`~/tools/quant_env/bin/python3`） | 表列表/分页浏览/排序可用 |
| TAVILY 依赖 server | deep-research 和 web-search 实测搜索 | 返回结果而非 "TAVILY_API_KEY not set" |
| graphify 数据存在 | `ls ~/brain/graphify-out/graph.json` | 文件存在（不是 /tmp/hermes-graph/）|
| 环境变量可达 MCP | `echo $TAVILY_API_KEY \| wc -c` | > 20 |
| **MCP 进程数 = 预期数** | `for srv in mcp-graphify mcp-mysql mcp-hermes-cron; do echo "$srv: $(ps aux | grep $srv'.py' | grep -v grep | wc -l)"; done` | 每个 server 应恰好 1 个进程。graphify 常因 cron 触发累积到 5+ 个 → 进程撞车导致 graphify-daily 静默失败 |

**MCP 进程清理**（当某 server 进程 > 1 时）：
```bash
# 保留最新进程，杀掉其余
ps aux | grep mcp-<server>.py | grep -v grep | sort -k11 | head -n -1 | awk '{print $2}' | xargs kill
# 或全杀等 gateway 自动重启
pkill -f "mcp-<server>.py" && sleep 2
systemctl --user restart hermes-gateway.service
```

**典型故障**：
- MCP server 连通但功能不可用（如 web-search server 运行正常但搜索报 TAVILY 未配置）→ `.env` 已更新但 gateway 未重启
- graphify server 连通但 `graph_stats` 报文件不存在 → 路径不匹配（硬编码 /tmp 而非 ~/brain/），见 `references/knowledge-pipeline-check.md`
- whisper-stt 报 "Method not found" 在 `list_prompts`/`list_resources` → 可选接口未实现，核心工具（transcribe）正常则无影响
- graph_stats 返回 edges=0 → 图构建时关系抽取失败，需重跑 graphify

**知识管道全链路**: memory→hindsight→gbrain→graphify→wiki 端到端检查见 `references/knowledge-pipeline-check.md`。
hindsight 部署与故障排查见 `references/hindsight-deployment.md`。

**修复**：重启 gateway `systemctl --user restart hermes-gateway.service` 让 MCP server 重新读取环境变量。

### 22.5 MCP 进程累积故障模式（v1.9 新增）

**场景**：MCP 工具全部显示红色故障状态，调用报 CancelledError。ps aux 显示 2-3x 预期 MCP 进程数。

**根因**（Hermes mcp_tool.py 第 259/1496-1526 行）：
```python
_MAX_INITIAL_CONNECT_RETRIES = 3  # 第 259 行
```
初始化阶段连接超时后，`run()` 循环 retry 每次重新调用 `_run_stdio(config)`（第 1461 行），而 `_run_stdio` 中的 `stdio_client(server_params)`（第 1222 行）每次都 spawn 新子进程。旧进程不被清理，导致每个 MCP 服务器 2-3 个副本。gateway 多次重启后，孤儿进程累积到 60+ 个，MCP 客户端被冲垮。

| 现象 | 原因 | 修复 |
|:-----|:-----|:-----|
| 全部 MCP 工具红色故障 | 进程累积导致连接 CancelledError | 全量清理后重启 |
| 单个 gateway session 内各 MCP 2-3 副本 | 初始化阶段 retry 未复用已有进程 | 增加 connect_timeout 减少超时；或改代码 |
| gateway 重启后进程翻倍 | 旧 MCP 孤儿进程未清理 | 先 stop gateway 再批量 pkill |

**修复流程**（已验证有效）：

```bash
# 1. 停 gateway
systemctl --user stop hermes-gateway.service

# 2. 用 xargs 批量杀全部 MCP 进程（pkill 在 shell 中可能被自身杀死）
ps aux | grep -E 'mcp-|stock-mcp|mcp-server|sequential-thinking' | grep -v grep | awk '{print $2}' | xargs -r kill 2>/dev/null
sleep 3
ps aux | grep -E 'mcp-|stock-mcp|mcp-server|sequential-thinking' | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null

# 3. 确认清空
ps aux | grep -E 'mcp-|stock-mcp|mcp-server|sequential-thinking' | grep -v grep | wc -l
# 预期: 0

# 4. 启动 gateway
systemctl --user start hermes-gateway.service

# 5. 等待 90 秒让所有 MCP 服务器完成初始化 + 连接
# 此期间不可操作——一旦杀"多余"进程，gateway 会检测到子进程死亡并重生新进程

# 6. 验证
systemctl --user status hermes-gateway.service 2>&1 | grep Tasks
# 预期: Tasks: 100+（含 MCP 子进程）
# 检查 errors.log 无新 CancelledError
grep 'mcp_tool' ~/.hermes/logs/errors.log 2>/dev/null | grep -v "$(date +%Y-%m-%d)" | head -3
```

**注意**：清理后在当前 CLI 会话中 MCP 工具仍不可用——工具表在会话启动时注册。需开新会话才能恢复。

**进程计数陷阱**：`ps aux | grep mcp-mysql | wc -l` 会误计 npx 的子线程（npm exec、sh、node 全部匹配）。精确计数法：

```bash
# 方法 1: 只看根进程
ps aux | grep -E 'python3.*mcp-.*\.py' | grep -v grep | awk '{for(i=11;i<=NF;i++) printf "%s ", $i}' | sort | uniq -c | sort -rn

# 方法 2: pstree（只看 gateway 的子进程）
PID=$(systemctl --user show hermes-gateway.service -p MainPID 2>/dev/null | cut -d= -f2)
pstree $PID -p 2>/dev/null | grep -E 'python.*mcp|node.*stock|uvx.*mcp|npm exec' | wc -l
```

**长期方案**：需改 Hermes 源码 `tools/mcp_tool.py` —— retry 前检查已有子进程是否存活，存活则复用连接而非 spawn 新进程。

### 23. 会话目录臃肿检测（v1.6 ⚠️ 关键）

会话文件是最隐蔽的臃肿源——`auto_prune: false` 会导致无限累积，实测 494MB/1156 文件。

| 检查项 | 方法 | 通过条件 |
|:-------|:-----|:---------|
| sessions 体积 | `du -sh ~/.hermes/sessions/` | < 200MB |
| 会话文件数 | `ls ~/.hermes/sessions/session_*.json \| wc -l` | < 300 |
| cron vs 用户比例 | `ls session_cron_*.json \| wc -l` | cron 会话应 < 总体的 30% |
| auto_prune 开启 | `grep -A1 'auto_prune' ~/.hermes/config.yaml` | `auto_prune: true` |
| 最旧会话 | `ls -t ~/.hermes/sessions/session_*.json \| tail -3` | 不应超过 retention_days |

**修复（三管齐下）**：
```bash
# 1. 开启 auto_prune
# 在 ~/.hermes/config.yaml 中: auto_prune: true, retention_days: 7

# 2. 删除所有 cron 会话（瞬时垃圾，占大头）
find ~/.hermes/sessions -name 'session_cron_*.json' -delete

# 3. 删除 7 天前用户会话
find ~/.hermes/sessions -name 'session_*.json' -mtime +7 -delete

# 4. 删除旧 JSONL 格式
rm -f ~/.hermes/sessions/*.jsonl
```

**根因**：每个 cron job 执行产生一个会话文件（~500K），25个job × 多频率 = 天增量 50+ 文件。即使 cron 精简到 17个，仍建议保持 auto_prune=true。

### 24. 域目录熵增检测（v1.3）

根目录干净不等于域目录干净。子代理在无 OUTPUT_DIR 约束时会在域根目录散落 v1-vN 试探脚本、调试截图、JSON dump。

| 检查项 | 方法 | 通过条件 |
|:-------|:-----|:---------|
| PDD 根试探脚本 | `ls ~/PDD/*_v[1-9]*.py ~/PDD/{react_fiber_explorer,spec_dom_investigation,study_draft_dom}*.py 2>/dev/null` | 无输出 |
| PDD 调试截图 | `ls ~/PDD/{csv_check,draft,spec_,service,slider,after}_*.png 2>/dev/null` | 无输出 |
| PDD JSON dump | `ls ~/PDD/{form_,react_,spec_,ai_}*.json 2>/dev/null` | 无输出 |
| quant 根临时脚本 | `ls ~/quant/{check_cache,debug,clean_parquet,backfill}*.py 2>/dev/null` | 可容忍少量（<5），但需定期清理 |
| 域根的 __pycache__ | `find ~/PDD ~/quant ~/tools -maxdepth 1 -name __pycache__ -type d` | 无 |

**熵增根因**：`delegate_task` 时未传 `OUTPUT_DIR` → 子代理不知放哪 → 随手丢域根。修复见 `subagent-delegation-protocol` skill 的 OUTPUT_DIR 强制规则。

**修复方式**：
```bash
# 清理空 skill 目录
find ~/.hermes/skills -empty -type d -delete

# 清理 __pycache__
find ~/.hermes/skills -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null

# 删除根目录孤立 package 文件
rm -f ~/package.json ~/package-lock.json

# 删除 skill 克隆缓存（如果技能已安装完）
rm -rf ~/tools/skill-repos
```

**.env 行号污染修复**（当行首有 `21|DEEPSEEK_API_KEY=...` 这种格式时）：
```bash
python3 -c "
import re
with open('/home/pebynn/.hermes/.env') as f:
    content = f.read()
cleaned = re.sub(r'^\d+\|', '', content, flags=re.MULTILINE)
with open('/home/pebynn/.hermes/.env', 'w') as f:
    f.write(cleaned)
"
```

**venv GPU 清理**（当 venv > 5GB 时）：
```bash
# 检查是什么占了空间
du -sh ~/.hermes/hermes-agent/venv/lib/python3.11/site-packages/{nvidia,torch,triton}/ 2>/dev/null

# 安全删除（无 GPU 的机器）
rm -rf ~/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/
rm -rf ~/.hermes/hermes-agent/venv/lib/python3.11/site-packages/torch/
rm -rf ~/.hermes/hermes-agent/venv/lib/python3.11/site-packages/triton/
rm -rf ~/.hermes/hermes-agent/venv/lib/python3.11/site-packages/cuda*/ 2>/dev/null
rm -rf ~/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia_*/ 2>/dev/null
```
典型回收：7.2G → 2.8G（省 4.4G）。

**.env 清理流程**（当 .env > 100 行时）：
1. 用 `grep -v '^#' .env | grep -v '^$' | grep '='` 提取所有活跃变量（通常 30-40 个）
2. 用 `grep -c '^#' .env` 确认注释行数
3. 重写 .env：简短头部 + 仅保留活跃变量分组排列
4. 删除已禁用平台的凭证（QQ_*, OLLAMA_*, 等）
5. 验证：`source ~/.hermes/.env && echo $DEEPSEEK_API_KEY` 能正常输出

## 漂移修复流程（发现问题后的标准化修复）

当诊断发现配置/SOUL.md漂移时，按以下顺序修复：

### Step 0: 决定 local profile 的去留

**选项 A: 维护 local profile（保留）**
如果决定保留，local profile 是默认激活的 profile，优先级高于主 config。不要在两者间来回修：
- 列出主 config 已优化的项，逐项在 local profile 中同步
- 如果 local profile 内有已经过时的 provider，一并删除

**选项 B: 直接删除 local profile（推荐）**
local profile 导致配置双份维护，且容易无声覆盖主 config 的优化。如果决定删除：
1. 先检查 local profile 的独有配置：
   ```bash
   diff <(grep -E '^[a-z]' ~/.hermes/config.yaml | sort) <(grep -E '^[a-z]' ~/.hermes/profiles/local/config.yaml | sort)
   ```
   最常见差异是 `delegation.api_key` — local profile 可能包含它，主 config 没有。
2. 迁移独有配置到主 config：
   ```bash
   # 例: migration delegation.api_key
   # 在 main config.yaml delegation 段中添加 api_key 行
   ```
3. 确认 `~/.hermes/SOUL.md` 和 `~/.hermes/profiles/local/SOUL.md` 内容一致（直接覆盖）
4. 删除 local profile：
   ```bash
   rm -rf ~/.hermes/profiles/local/
   ```
5. 删除 memory 中关于 local profile 的旧记录

**验证**：`ls ~/.hermes/profiles/` 不应包含 local

### Step 1: 全量主 Config 优化

对 config.yaml 执行以下标准化检查（推荐值）：

| 配置项 | 推荐值 | 原因 |
|:-------|:-------|:-----|
| `model.default` | `deepseek-v4-flash` | 快速模型做主力，避免误用 reasoning 模型 |
| `display.personality` | `concise` | 匹配用户偏好（简洁干练） |
| `display.show_cost` | `true` | 跟踪 API 花费 |
| `web.backend` | `tavily` | 比 duckduckgo 结果更精准 |
| `sessions.auto_prune` | `true` | 90天 retention 自动清理 |
| `logging.max_size_mb` | `50` | 5MB 太小，日志频繁被截断 |
| `cron.max_parallel_jobs` | `3` | 无限并行会争资源 |
| `memory_char_limit` | `12000` | 6KB→12KB 提升记忆容量 |
| `auxiliary.vision.provider` | `deepseek` | auto 可能选到不支持多模态的模型 |
| `fallback_model.provider` | `deepseek` | 和主模型同 provider，不用额外 API key |
| `fallback_model.model` | `deepseek-v4-flash` | 主模型不可用时的备胎（deepseek-chat 已于2026-04下架） |

**config.yaml 瘦身检查**（删除以下类型的不必要的配置行）：
- 未使用的 personality（只保留 `concise`）
- local 后端下无效的 container 配置（docker_image/singularity_image/modal_image/container_cpu/memory/disk/volumes）
- 禁用平台的配置块（discord/whatsapp/telegram/slack/mattermost 的空 `{}` 块）
- 整个 bedrock 区块（如果不用 AWS）

**关键认知：** local profile（如存在）优先级高于主 config，配置修改必须改 local profile 才生效。如果主 config 优化后 local profile 仍保留旧值，优化等于没做。**推荐直接删除 local profile**（见 Step 0 选项B）。

### Step 2: 工具层（platform_toolsets + auxiliary）优化

| 检查项 | 操作 |
|:-------|:-----|
| 不用的平台（telegram/discord/whatsapp/slack/signal/homeassistant） | 在 `platform_toolsets` 中注释掉，gateway 启动时不尝试初始化 |
| QQ Bot（如果凭证无效） | 两处配合：config.yaml 注释 + .env 删除 QQ_* 变量 |
| `bedrock.discovery.enabled` | 设为 `false`（不用 AWS Bedrock 的话） |
| `bedrock.guardrail` 段 | 如果不用 AWS 可安全删除或留空 |

### Step 3: SOUL.md 规则一致性修复

**问题：规则 1 和规则 8 的矛盾**
```
规则 1 说: patch/write_file/terminal(foreground) 禁止
规则 8 说: 基础设施故障时可以用这些工具
```
修复：规则 1 分层为三档：
```
**绝对禁止**：browser_click, browser_navigate, browser_type, browser_press, browser_scroll, execute_code（无例外）
**原则上禁止，自愈通道(Rule 8)可例外**：patch, write_file, terminal(foreground)（仅修复 delegation 基础设施）
**允许**：delegate_task, terminal(background), web_search, web_extract, read_file(检查输出), memory, session_search, skill_view, todo, cronjob, browser_snapshot, browser_console, browser_vision, browser_get_images, vision_analyze, image_generate, clarify, text_to_speech
```
规则 8 开头加：`> ⚠️ **本规则优先于规则 1。** 规则 1 的禁止列表中的 patch、write_file、terminal(foreground) 在本规则范围内可用。`

同时同步到主 SOUL.md 和 local profile SOUL.md（如果 local 存在）。

### Step 4: 修复域 SOUL.md

逐域检查身份文件，标准化：
1. **修正事实错误** — 如宣称"跨三平台"实际只有单一数据源
2. **统一矛盾参数** — 如旧分域时退货率在 ec-pdd SOUL 写 18% 但在 memory 中是 25%，合并到 ec-domain 后已统一
3. **补充 toolsets 声明** — 每个域 SOUL.md 末尾加 `可用工具集` 节，明确 delegate 时应传入的 toolsets
4. **补充实际工作流** — 简洁的子代理 SOUL（< 30 行）通常缺具体操作指引，至少扩到 60+ 行
5. **补充具体路径和命令** — 代理应当知道脚本在哪、用什么命令调用
6. **统一子代理语气** — code-domain 的"立即编写高质量代码"应改为"由总指挥调度处理编码任务"
7. **添加 配合技能 章节** — 每个域 SOUL.md 末尾加 `配合技能` 节，列出现有技能中与本域相关的工具（如 research-domain 引用 web-researcher/parallel-cli/jina-reader/crawl4ai）
8. **验证所有引用一致性** — 配合技能中引用的 skill 必须在 `~/.hermes/skills/` 中实际存在

### Step 5: Skills 清理

| 检查项 | 操作 |
|:-------|:-----|
| 空分类目录（0 SKILL.md） | `find ~/.hermes/skills -empty -type d` 删除 |
| 过时架构文档型技能 | 检查 `ec-development-duo-architecture`（旧版文档）、`multi-agent-architecture`（通用理论[已落地]）等是否可删除 |
| 分类目录数量 | 保持 8-10 个活跃分类，删除空壳 |

### Step 6: 验证
```
# 确认 toolsets 声明完整
grep '可用工具集' ~/.hermes/profiles/*/SOUL.md

# 确认矛盾参数已统一（无退-18% 或 退-25% 混用）
grep -i '退货率\|退-*%' ~/.hermes/profiles/*/SOUL.md

# 确认 platforms 无无效服务
grep -A1 'qqbot\|platform_toolsets' ~/.hermes/config.yaml | head -5

# 确认 bedrock discovery 已关
grep -A2 'discovery' ~/.hermes/config.yaml
```

### Step 7: 清理记忆
Memory 中可能残留已卸载/已更改工具的旧记录（如 ollama、local profile），remove 掉即可。

## 执行方式

### 自动模式（推荐 — 由 agenda_builder.py v2.0 替代）

日常健康检查现在由 `~/.hermes/scripts/agenda_builder.py` (v2.0, 350行) 自动执行，通过 cron `e512e447fb29` 每天 08:00 运行。该脚本已包含：
- 服务健康 (Gateway/MySQL/DeepSeek/Camofox)
- Cron 状态解析 (hermes cron list 文本解析)
- 数据新鲜度 (MySQL K线行数 + 复盘草稿)
- 资源趋势 (磁盘/内存/会话 + 昨日对比)
- 错误情报 (13类噪音过滤 + 按类别分组)
- 管道日程 (今日预期执行的任务)

输出为 `~/.hermes/agenda/daily.md`，供 `ops-autopilot` cron (08:05) 自动处理。

详见 `agent-self-maintenance` skill → `references/autonomous-ops-pipeline.md`。

### 手动触发

### 综合评分模式（新增）

当用户要求"给自己打分"或"从多维度评估"时，使用10维度评分框架。详见 `references/scoring-framework-10dim.md`。

评分流程：
1. 并行拉取全维度数据（cronjob list / graph stats / 磁盘 / 技能数 / config / memory使用率 / orchestrator开关）
2. 按10维度分别打分（1-100）
3. 加权计算综合分
4. 输出评分矩阵 + 硬伤TOP3

### 手动触发

直接说"自检"或"健康检查"时执行。

**推荐混合执行模式**（本session验证最优）：
```
# 主代理直接并行快检（无delegate开销）：
→ cronjob list
→ mcp_graphify_graph_stats
→ memory (查看usage%)
→ terminal: disk/venv/.env/技能数/Camofox/Gateway

# 同时并行派发深度审计：
→ [派发 → ops-domain] 系统服务 + 域熵增 + checkpoints + GPU包
→ [派发 → code-domain] 配置审计 + Profiles + 技能生态 + 过时技能
```
快检项 5-10 秒完成，深度审计 2 个 delegate 并行 3-4 分钟。总计 3-4 分钟，比 5 路 delegate 更省 token。

**自动清理模式**：当用户说"你判断后动手"/"直接修"时，以下零风险项自动执行不询问：
- `find ~/.hermes/skills -empty -type d -delete`
- `find ~/.hermes/skills ~/.hermes/profiles -name __pycache__ -type d -exec rm -rf {} +`
- `ls -1t ~/.hermes/checkpoints/ | tail -n +11 | xargs rm -rf` （保留最近10个）
- `find ~/.hermes/sessions -name 'session_cron_*.json' -delete` （删除瞬时垃圾）
- `grep -q 'auto_prune: false' ~/.hermes/config.yaml && echo 'WARN: auto_prune disabled'` （检查配置漂移）
- 过时profile技能删除（需先确认无cron/SOUL引用）

**串行模式**（保留，适合逐项排查）：
按上面 20 节逐项运行 bash 命令，一次一项，适合排查特定问题时用。

### 自动触发

每周一凌晨5点通过 cron 自动执行，仅当发现具体问题时才汇报给用户。

## 汇报格式

```
✅ 健康检查通过 — 所有域正常 | 或
⚠️ 部分异常 — 详情见下

[域] 状态 | 异常项 | 影响 | 建议操作
```

## 规则

- 没异常不打扰用户（安静自检）
- 有异常才汇报（具体问题 + 影响范围 + 修复方案）
- 能自动修复的直接修，只在汇报中注明
- **发现即修复铁律（2026-05-08 强化）**：当用户要求进度回顾/评分/评估时，发现的L1级别问题必须立即动手修复，不可只列举不行动。用户要的是"修好了"不是"找到了"。
- **全域扫描原则**：排查问题时不要只盯着当前域。写作域的问题根因可能出在量化域（共享数据源/函数），反之亦然。先画拓扑再动手。
- **False alarm = 信用损耗**：未确认的问题不要说死了。"MySQL权限被拒"先确认是自己的SQL写错了库名，还是真的权限问题。拿不准说"正在排查"，不输出未验证的结论。
