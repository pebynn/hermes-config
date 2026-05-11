---
allowed-tools:
- delegate_task
- file
- search
- memory
arguments:
- description: 任务目标（简短、精确）
  name: goal
  required: true
- description: 完整的背景信息（路径、参数、约束、失败处理）
  name: context
  required: true
- default: leaf
  description: 子代理角色 (leaf|orchestrator)
  name: role
- default:
  - terminal
  - file
  description: 工具集
version: 2.2.0
author: unknown
description: 子代理委托协议 — 集成 Claude Code AgentTool + 并行编排 + 上下文压缩 最佳实践。注意：在纯kanban架构中，delegate_task不出现于总指挥层，只存在于kanban worker内部。
hooks:
  post-delegate:
  - 检查结果是否为空或有错误
  - 失败时分析日志并重新派发
  pre-delegate:
  - 确保 goal 自包含（子代理不知道父会话历史）
  - 确保 context 传完整约束（路径、参数、公式、失败处理）
  - 评估子代理需要的工具集
  timeout:
  - 10分钟无返回 → 汇报给用户
  - 连续失败2次 → 降低复杂度重试
name: subagent-delegation-protocol
version: 2.1.0
when-to-use: '任何需要 delegate_task 派发任务给子代理的场景。

  这是纯调度模式的核心委托协议。

  当任务需要跨会话持久化/多阶段依赖图/硬阻断门禁时，考虑升级到 Kanban 架构。

  决策参考: references/delegate-task-vs-kanban.md

  '
---
# 子代理委托协议 — Claude Code 启发版

## 核心原则

借鉴 Claude Code AgentTool 的设计：
1. **自包含目标** — 子代理是独立的 LLM 会话，不知道父会话历史
2. **全上下文传递** — 类比 Claude Code 的 forkSubagent: 传所有必要约束
3. **工具隔离** — 子代理只获得任务所需的工具集
4. **先计划后执行** — 子代理接到任务必须先出实施计划（需求理解→技术方案→文件清单→步骤），总指挥审核通过再动手。子代理间协作也遵循此规则（主SOUL.md 规则9）
5. **超时与兜底** — 10分钟超时汇报，连续失败重试

## 委托模式

### 单任务委托

```python
# 最基本的委托
result = delegate_task(
    goal="运行选品管线",
    context="品类: 中老年女装, 最大商品: 8, 账号: 17825029430",
    toolsets=["terminal", "file"]
)
```

**Claude Code 对比**：相当于 `AgentTool({ description: "选品", prompt: "...", subagent_type: "general-purpose" })`

### 并行批处理（batch）

```python
# 无依赖的任务并行执行
results = delegate_task(tasks=[
    {"goal": "采集热词", "context": "...", "toolsets": [...]},
    {"goal": "调研竞品", "context": "...", "toolsets": [...]},
])
```

**Claude Code 对比**：相当于 `TeamCreateTool` + 多 agent 并行 + `SendMessageTool`

### 流水线委托（串行）

```python
# A 的结果作为 B 的输入
result_a = delegate_task(goal="分析日志找出错误", context="...")
result_b = delegate_task(goal=f"修复错误: {result_a}", context="...")
```

**Claude Code 对比**：相当于 forkSubagent 继承上下文 + 后续 tool call 继续

### 编排器模式

```python
# 子代理自己可以进一步拆解任务
result = delegate_task(
    goal="完成选品上架管线",
    context="全流程: 采集→17网搜索下载→去水印→上架准备→PDD预览",
    role="orchestrator"  # 保留 delegate_task 能力
)
```

**Claude Code 对比**：相当于 `COORDINATOR_MODE` + 内置 agent 树

## 并行执行（超越 Claude Code）

借鉴 Claude Code 的 `runTools`/`toolOrchestration.ts` 模式：
- 只读操作（read_file, web_search, web_extract）→ **并行执行**（最多3个）
- 写操作（terminal写文件, delegate_task写结果）→ **串行执行**
- 每个 delegate 实际上是"工具调用"，因此同一 batch 中：

```python
# ✅ 正确：读操作并行
delegate_task(tasks=[
    {"goal": "搜索17网中老年女装热词", "toolsets": ["web"]},
    {"goal": "搜索抖音中老年女装趋势", "toolsets": ["web"]},
    {"goal": "查昨天选品的listing-ready输出", "toolsets": ["file"]}
])
# 3个只读任务 → 并行执行

# ✅ 正确：写操作串行
result_a = delegate_task(goal="下载商品A", ...)
result_b = delegate_task(goal="下载商品B", ...)
# 下载是写操作 → 必须串行

# ✅ 最佳实践：混合模式
# 先并行读，再串行写
read_results = delegate_task(tasks=[读A, 读B, 读C])    # 并行
write_result = delegate_task(goal=f"基于{read_results}执行写操作", ...)  # 串行
```

## 上下文压缩（超越 Claude Code）

借鉴 Claude Code 的 compact 系统和 toolResultBudget：

### 何时压缩

| 条件 | 操作 |
|:----|:----|
| 一个 delegate 返回结果 > 5KB | 只保留摘要（状态 + 路径 + 关键数字） |
| 同一会话中已执行 > 30 次工具调用 | 触发上下文清理 |
| 子代理结果在 30 分钟前 | 标记为 `[STALE]`，不传给下一个 delegate |
| 连续 3 个同链路的 delegate | 只保留最后一个的结果摘要 |

### 压缩格式

```python
# 压缩前（~8KB）
result = delegate_task(goal="选品8件中老年女装", ...)
# 包含：采集日志、搜索过程、全部7个商品的下载日志、每个图片的处理记录

# 压缩后（~500B）——只保留这个传给下一个delegate
"""
|[ec-domain sourcing 阶段 摘要]
- status: success (7/8件成功, 1件失败: 盛达网购-353吊带裙不适合品类已跳过)
- output: ~/PDD/商品/2026-04-28/listing-ready/
- 推荐款: 卡彤网批冰丝衬衫(¥69.9, 18SKU), 恒旺网批国风T恤(¥49.9)
- 价格区间: ¥9-¥39
- 详细日志在: ~/PDD/商品/2026-04-28/download_log.txt
"""
```

### 与 Claude Code 的差异

| 特性 | Claude Code | Hermes 改进 |
|:----|:-----------|:-----------|
| 压缩时机 | 用户触发 /compact 或自动 | 在每次 delegate 前自动判断 |
| 压缩粒度 | 整个对话历史 | 仅压缩已完成的子代理结果 |
| 恢复能力 | /resume 恢复会话 | read_file 直接读任意输出文件 |
| 信息精度 | LLM 摘要可能丢细节 | 结构化摘要 + 文件级追溯 |

## 子代理类型

借鉴 Claude Code 的 `subagent_type` 概念：

| 类型 | 角色 | 适用场景 | 可用的工具集 |
|:----|:----|:--------|:-----------|
| `leaf` | 叶子节点 | 执行单一任务（默认） | 无 delegate_task |
| `orchestrator` | 编排器 | 可拆解复杂任务给更小的子代理 | 含 delegate_task |

部署限制：
- 最大嵌套深度：`delegation.max_spawn_depth`（默认2）
- 最大并行子代理：`delegation.max_concurrent_children`（默认3）

## Context 设计清单

子代理 context 应包含以下信息（类比 Claude Code 的 `CacheSafeParams`）：

```
1. GOAL: 一句话说清楚要干什么
2. FILE_PATHS: 输入文件的完整路径
3. OUTPUT_DIR: 产出文件的目录（强制指定，禁止随意散落根目录或域根目录）
4. PARAMETERS: 关键参数和默认值
5. CONSTRAINTS: 限制条件（品类方向、风格、价格范围）
6. FAILURE_HANDLING: 出错时怎么处理
7. EXPECTED_OUTPUT: 期望产出的格式
```

### ⚠️ OUTPUT_DIR 强制规则

**不指定 OUTPUT_DIR 的委托是违规操作。** 子代理缺乏父会话上下文，不知道用户的文件组织规则（根目录不留文件、量化→~/quant/、电商→~/PDD/、临时→~/tmp/），因此必须显式传输出路径。

| 任务类型 | 默认输出路径 | 示例 |
|:--------|:-----------|:-----|
| PDD调试脚本 | `~/PDD/` | `OUTPUT_DIR: ~/PDD/` |
| PDD截图 | `~/PDD/screenshots/` | `OUTPUT_DIR: ~/PDD/screenshots/` |
| 量化脚本 | `~/quant/` | `OUTPUT_DIR: ~/quant/` |
| 微信推送 | `~/PDD/运营/` | `OUTPUT_DIR: ~/PDD/运营/` |
| 临时调试 | `/tmp/` | `OUTPUT_DIR: /tmp/hermes_debug_YYYYMMDD/` |
| 文档产出 | `~/文档/` | `OUTPUT_DIR: ~/文档/` |
| 研究产出 | `~/research-skill-graph/projects/<name>/` | 按 deep-research 协议 |

**反例**（导致熵增）：
```
❌ delegate_task(goal="写个脚本试下CSV导入", context="...")  
   → 子代理把 pdd_csv_import.py 丢 ~/ → 根目录又多一个垃圾文件
   
✅ delegate_task(goal="写个脚本试下CSV导入", 
                 context="OUTPUT_DIR: ~/PDD/ ...")
   → 子代理知道放哪
```

**历史教训**：2026-05-04 清理了根目录 158 个散落文件 + PDD 内 92 个 v1-vN 试探脚本，根因即委托时未指定输出目录。

## 流水线 Context 继承（超越 Claude Code）

Claude Code 的 forkSubagent 只继承父会话上下文。Hermes 更进一步：**跨代理间的结构化数据传递**。

### 流水线模式

```python
# Stage 1: sourcing → 输出结构化结果
result_1 = delegate_task(goal="选品采购 8件中老年女装", ...)
# result_1 = {
#   "status": "success",
#   "products": 7,
#   "output_dir": "~/PDD/商品/2026-04-27/listing-ready/",
#   "recommended": ["卡彤网批冰丝衬衫", "恒旺网批国风T恤"],
#   "prices_range": "¥9-¥39"
# }

# Stage 2: 继承 result_1 的产出路径，pdd 直接消费
result_2 = delegate_task(
    goal=f"PDD上架: 处理 sourcing 输出的 {result_1['output_dir']}",
    context=f"""
继承自 sourcing 的数据:
- 商品数量: {result_1['products']}
- listing-ready 路径: {result_1['output_dir']}
- 推荐重点款: {result_1['recommended']}
- 价格区间: {result_1['prices_range']}
    """,
    ...
)

# Stage 3: fulfillment 继承全部上下文
result_3 = delegate_task(
    goal=f"订单履约准备: sourcing({result_1['products']}件) + pdd已完成上架",
    context=f"""
全链路上下文:
- 已选品: {result_1['products']}件 在 {result_1['output_dir']}
- 已上架: {result_2['listing_results']}
- 需要准备订单处理
    """,
    ...
)
```

### 优势对比

| 特性 | Claude Code forkSubagent | Hermes 流水线继承 |
|:----|:------------------------|:-----------------|
| 上下文范围 | 继承父会话完整上下文 | 传递结构化任务结果 |
| 缓存共享 | 字节级系统提示注入 | 精简的跨代理数据 |
| 代理间通信 | SendMessageTool | context 字段传参 |
| 失败回溯 | 全链路重试 | 可精确定位到阶段 |

这就是超越 Claude Code 的地方：**不是无脑继承全部上下文，而是智能传递结构化的工作产出**。

## 动态协作（Dynamic Collaboration）

### 统一子代理返回协议

子代理完成任务、被阻塞或预计超时时，通过结构化返回结果驱动主代理调度：

```
status: "success" | "blocked" | "failed" | "handoff"
需要: 协作需求或遇到的问题（不指名具体域）
详情/路径: 补充说明；handoff 时填写脚本路径和运行命令
```

### 自动调度逻辑

| 子代理状态 | 主代理动作 |
|-----------|-----------|
| blocked + 需要 | 根据"需要"对照可调度资源表判断对应域，调其处理后再重试 |
| success | 正常返回，不做额外调度 |
| failed + 错误信息 | 分析日志降复杂度重试 |
| handoff + 路径 | `terminal(background)` 跑脚本，干别的，通知到了读结果 |

### 需要→域映射规则

主代理根据子代理描述的"需要"，对照可调度资源表（SOUL.md 中的域职责表）判断该调哪个域。不硬编码映射关系，由域职责描述自然推导。

### 示例：sourcing 被验证码阻塞

```python
r = delegate_task(goal="ec-domain: sourcing 选品")
# r 返回:
#   status: "blocked"
#   需要: "验证码识别"
#   详情: "17网登录页出现图片验证码"

# 对照可调度资源表 → "编码"相关 → code-domain
fix = delegate_task(goal="code-domain: 写验证码识别脚本", context=r['详情'])
retry = delegate_task(goal="ec-domain: 继续选品", context="验证码已处理")
```

### handoff 协议（子代理执行中预计超时）

子代理打包剩余工作到 `~/.hermes/background_jobs/`，返回结构化结果：

```
{status: "handoff", 需要: "超时处理", 路径: "脚本路径", 命令: "运行命令"}
```

主代理：`terminal(命令, background=true, notify_on_complete=true)` → 干别的 → 通知到了读结果。

## 模型选择策略

不同任务类型需要不同的模型。选错模型会导致要么浪费钱（pro跑简单任务），要么超时（pro跑迭代开发太慢）。

### 模型速查

| 任务类型 | 推荐模型 | 理由 |
|:--------|:--------|:-----|
| 脚本开发（写→测→修） | **flash** | pro 响应 5-15s/次，迭代 20+ 次必超时。flash 1-2 分钟写完 |
| 数据分析/格式化输出 | **flash** | 数据已由 Python 计算好，LLM 只做翻译和排版 |
| 综合诊断/投资分析 | **pro** | 需要真正的推理判断和跨维度分析 |
| 长文本摘要/报告撰写 | **pro** | 指令遵循更稳，长上下文一致性更好 |

### 实践规则

1. **profile config.yaml 的 delegation.model 不生效** — 子代理不受 profile 配置影响
2. **delegate_task(model="...") 显式传参有效** — 必须调用时手动传
3. **写脚本类任务用 flash + 加 "写完不测试" 指令** — 总指挥收尾统一跑测，节省子代理调试时间
4. **flash 写脚本约 2 分钟，pro 写脚本约 8 分钟** — flash 在迭代开发场景速度快 4x

```python
# ✅ 脚本开发 → flash
delegate_task(goal="写脚本", model="deepseek-v4-flash", context="写完就停，不要测试")

# ✅ 分析推理 → pro
delegate_task(goal="综合诊断", model="deepseek-v4-pro", toolsets=["terminal","file","web","browser"])

# ❌ 不要用 pro 写脚本 — 会超时中断
```

## 超时与容错

借鉴 Claude Code 的 `AbortError` + 自动重试机制：

| 场景 | 行为 |
|:----|:----|
| 子代理10分钟无返回 | 汇报用户：谁+多久+在做什么+预计还需多久。**检查僵尸进程**：子代理超时后其后台进程可能仍存活，锁住共享资源（PGLite、文件锁等）。用 `ps aux | grep <关键词>` 查杀后再重试。 |
| 子代理卡住无新调用 | 中断并重新派发 |
| 子代理失败（有错误输出） | 分析日志找出原因 → 带着错误信息重新派发 |
| 连续失败2次 | 降低复杂度或用更简单的方法重试 |
| 全部失败 | 向用户报告失败原因和建议替代方案 |
| **delegate_task 系统报错**（如 API key 未配置、base_url 不可达、授权失败） | **禁止自行绕过**。不得替换为 web_search/terminal/write_file 等直接执行。必须向用户汇报：报错信息 + 根因分析 + 修复方案（需提供什么配置/凭证），等待用户处理后重试。 |

### 数据密集型任务反模式（2026-05-07发现）

**核心教训**: 数据密集型操作（MySQL bulk insert、5000+ parquet文件扫描、全市场数据采集）在子代理中几乎必超时。不要 delegate。

| 任务类型 | 子代理结果 | 正确做法 |
|:--------|:---------|:--------|
| MySQL bulk insert (5000+行) | 900s timeout, 24次API调用后卡死 | 主代理写pymysql脚本 → `terminal(background=true)` |
| 全量parquet扫描 (5293文件) | 777s interrupted, 14次调用 | 主代理写扫描脚本 → `terminal(background=true)` |
| 单脚本开发 (≤200行) | ✅ 正常 | delegate 到 code-domain |
| 代码分析+重构 | ✅ 正常 | delegate 到 code-domain |

**判断标准**: 如果任务需要遍历 >1000个文件、或写入 >1000条数据库记录，就是数据密集型任务，走主代理脚本+后台执行。

**对比**:
```
❌ delegate_task(goal="回填5000条K线到MySQL") → timeout
✅ write_file(backfill_kline.py) → terminal("python3 backfill_kline.py", background=true) → poll
```

**MCP工具故障模式 (2026-05-08)**: MCP MySQL在大批量写入时会断连(4次连续失败 → unreachable)。改用直接连接方式:
```python
# ❌ MCP bulk_insert 5000行 → 连续失败后 unreachable
# ✅ pymysql 直连 + executemany
conn = pymysql.connect(host="127.0.0.1", user="stock", password="***", db="stock_kline")
cursor.executemany(sql, batch)
# 或 mysql CLI 管道
mysql -u stock -p'***' stock_kline < insert.sql
```

**execute_code沙箱限制 (2026-05-08)**: execute_code使用系统Python，缺少pyarrow/fastparquet等库。parquet读取必须走terminal + quant_env:
```
❌ execute_code("pd.read_parquet(...)") → ImportError: pyarrow required
✅ terminal("/home/pebynn/tools/quant_env/bin/python3 -c 'pd.read_parquet(...)'")
```

**MySQL列映射铁律 (2026-05-08)**: 写入前必须读schema。parquet中文列名→MySQL英文列名映射不能靠猜:
- `成交额` → `amount` (decimal(16,2))
- `成交量` → `volume` (bigint)  
- `turnover` → 换手率 (decimal(12,10))，不是成交额

### 超时预防：任务粒度控制

**核心原则**：单次 delegate_task 的 API 调用链不要超过 ~20 次。

| 任务粒度 | 预估调用 | 风险 | 建议 |
|:---------|:--------|:----|:-----|
| 单研究项目（deep-research） | 15-25次 | 低 | 直接派，可以并行多个研究 |
| 创建单个技能 | 5-10次 | 低 | 直接派 |
| 整合多个研究→创建技能+更新SOUL.md | 25-40次 | **高（900s超时）** | 拆分为：先建技能，再更新SOUL.md |

**拆分策略**：
```
❌ 一个 task 塞：读3个研究项目 + 建3个技能 + patch已有技能 + 更新SOUL.md
   → 900s超时，23次调用后卡住

✅ 拆分为：
   task A: 建技能文件（只 create/patch 技能，不动 SOUL.md）
   task B: 更新 SOUL.md（读已有技能清单 → patch SOUL.md）
```

**超时后恢复**：检查目标目录是否已有部分产出（技能文件可能已写入），先确认已有文件质量再补缺，避免重复工作。

### delegate_task 基础设施故障排查

当 `delegate_task` 报系统级错误（非子代理执行失败，而是派发本身失败）时，用以下排查链：

**关键认知：纯调度模式下的架构死锁**

```
我（调度器）→ 禁止执行工具       ✋
子代理        → 需要 delegation 启动 🚫
delegation    → 配置/凭证有问题     💥
→ 三者互锁，无路可走
```

解法：**自愈通道** — 只有 delegation 基础设施不可用时，允许调度器有限使用执行工具（patch/write_file/terminal/execute_code）仅修复 delegation 本身。修复完立即锁回纯调度模式。自愈通道的完整定义见 `~/.hermes/SOUL.md` 规则 8。

**错误信息**：`"Delegation base_url is configured but no API key was found. Set delegation.api_key or OPENAI_API_KEY."`

**排查步骤（包含 profile-override 陷阱）**：

```
Step 1: 检查主配置
        ~/.hermes/config.yaml → delegation.api_key
        → 如果为空字符串 ''，说明配置了但没填 key
        → 如果整个 delegation 段不存在，说明没配置

Step 2: 检查 profile 覆盖（⚠️ 易漏点）
        ~/.hermes/profiles/*/config.yaml → 各 profile 的 delegation.api_key
        → 如果当前会话使用某个 profile（如 local），其配置会覆盖主配置
        → 即使主配置有 key，profile 里的 api_key: '' 也会让 delegation 失效
        → grep 所有 profile 的 api_key 做全面检查

Step 3: 理解凭证解析链（delegate_tool.py 源码）
        api_key = configured_api_key or os.getenv("OPENAI_API_KEY", "").strip()
        → 先从 config.yaml 读 api_key
        → 如果为空/None，fallback 到 OPENAI_API_KEY 环境变量
        → 都为空 → 报 ValueError

Step 4: 诊断当前会话状态
        Config 在会话启动时加载并缓存 —— 修改 config.yaml 后不会在本会话生效
        execute_code 每次跑在独立子进程，设 os.environ 不影响父进程
        terminal 设 export 仅影响该 shell 子进程，不影响 agent 进程
        → 需判断：是本会话的缓存问题，还是配置本身就没写对
        → sed -n 'Np' 确认文件实际内容（read_file 显示会截断长字符串）

Step 5: 修复路径
        方案A（持久修复）：
            1. patch ~/.hermes/config.yaml delegation.api_key 填入正确 key
            2. patch ~/.hermes/profiles/<active_profile>/config.yaml 也一样（如果有）
            3. 重启 Hermes 让新会话加载
        方案B（当前会话）：无法纯通过工具修复 —— 任何工具都在子进程环境执行
            需要用户重启 Hermes
```

**根因定位技巧**：
- `read_file` 显示 `sk-c39...8ee1` — 这是工具显示截断，不是文件内容截断。用 `sed -n 'Np' | od -c` 看真实内容
- 如果 config 已有 key 但仍报错 → 可能是 profile 覆盖，或会话缓存问题，必须重启
- 如果 config 中 `api_key` 为空字符串 → 是遗漏配置，检查主配置 + 所有 profile
- 子代理的 credential 解析在 `tools/delegate_tool.py` 约 2190-2200 行
- 多个 config 文件都有 `api_key` 时，grep 结果可能有几十行，注意区分 provider 用的 api_key 和 delegation 用的 api_key

## Role Chain — 多角色质量保障链（v3.0 新增）

借鉴 GitHub #344 多智能体架构提案，Role Chain 是对 `delegate_task` 的高级封装：**不是文本规则建议"应该审查"，而是脚本硬约束"不审查就阻断"**。

### 核心设计

不改动现有 domain agent（research/writing/finance/code 等），通过注入行为约束实现角色切换：

| Role | 复用域 | 注入约束 |
|:--|:--|:--|
| Researcher | research-domain | 只采集+标注来源，不做分析 |
| Creator | writing/finance/code-domain | 基于上游数据创作，不自采 |
| **Reviewer** | 独立 agent (新) | 只找错不修错，对照门禁审查 |
| **Synthesizer** | 独立 agent (新) | 格式整合+发布，不改内容 |

### 强制执行器: `role_chain.py`

```bash
python3 ~/.hermes/scripts/role_chain.py \
  --template publish-review \
  --task "生成今日复盘"
```

产出: 链定义 + 阻断点标记 → 主代理按序 delegate_task。Reviewer FAIL → 链终止。

### 链模板

| 模板 | 链 | 何时启用 |
|:--|:--|:--|
| `publish-review` | R→W→Rv→S | 公众号/消息推送 |
| `signal-review` | R→F→Rv | 量化信号/投资建议 |
| 数据分析(外发) | R→[domain]→Rv→S | 需外发的数据报告 |
| 内部任务 | 单 domain | 日常维护 |

### 阻断机制

```
role_chain.py 定义链
  → Reviewer 步骤标记 blocker=True
  → Reviewer FAIL → 链状态=blocked
  → Synthesizer 检查 require_reviewer_pass=True
  → 直接拒绝: "❌ Reviewer 未通过，发布阻断"
  → 不可能跳过 Reviewer 直接发布
```

每步写审计日志到 `~/.hermes/logs/role_chain/`，可追溯每个环节。

### 子代理质量评分

`role_chain.py` 的配套工具。独立评分，不依赖 Reviewer：

```bash
python3 ~/.hermes/scripts/quality_score.py \
  --output "子代理返回文本" \
  --goal "原始目标" \
  --domain writing
```

四维评分：数据准确(40) + AI味(20) + 合规(20) + 格式(20)
- PASS: ≥70 且无硬伤
- FAIL: <70 或有硬伤（自算数据、投资建议）→ 触发 Reviewer 复核

### 管道检查点

长任务中断恢复机制。每个 pipeline stage 完成后保存状态：

```bash
python3 ~/.hermes/scripts/pipeline_checkpoint.py save <pipe_id> <stage_id>
python3 ~/.hermes/scripts/pipeline_checkpoint.py resume <pipe_id>  # → 下一阶段
python3 ~/.hermes/scripts/pipeline_checkpoint.py clear <pipe_id>   # 完成后清理
```

### 与现有模式的关系

| 模式 | 适用场景 | 特点 |
|:--|:--|:--|
| 单 agent delegate | 低风险日常任务 | 最快，0 额外成本 |
| 并行 delegate | 无依赖多任务 | 已在 batch 模式支持 |
| Role Chain | 高风险外发任务 | +200% API 成本，质量保障 |
| Pipeline | 多阶段跨天任务 | checkpoint 恢复 |
| **Kanban 原生 Role Chain** | **kanban 架构下的外发任务** | **0 额外脚本，kanban 依赖图替代 role_chain.py** |

### Kanban 架构对 Role Chain 的替代（2026-05 审计结论）

在 kanban+delegate_task 共存架构中（总指挥纯 kanban 路由，worker 内部用 delegate_task），Role Chain 的三个脚本被 kanban 原生机制替代：

| 脚本 | 被替代为 | 理由 |
|:--|:--|:--|
| `role_chain.py` | kanban 依赖图 + 独立 worker profile | 链定义=parents 依赖，阻断点=blocker worker，角色约束=独立 system prompt |
| `quality_score.py` | reviewer worker 的 kanban_complete metadata | 评分由 reviewer worker 在 metadata 中输出结构化 findings |
| `pipeline_checkpoint.py` | kanban SQLite 持久化 | 所有 kanban 任务天然持久化，中断后自动恢复 |

kanban 架构下的 Role Chain 流程：
```
kanban_create(T1: researcher, parents=[])
kanban_create(T2: writer, parents=[T1])
kanban_create(T3: reviewer, parents=[T2])  ← 只读不写，FAIL→kanban_block
kanban_create(T4: publisher, parents=[T3]) ← T3 FAIL 自动阻断
```

与 data_guard.py 仍是互补关系，data_guard 管数据质量，reviewer worker 管内容质量。但在 kanban 架构中不再需要额外的 Python 脚本来管理角色链——kanban 的依赖图和独立 worker 原生解决了这个问题。

### 与 data_guard.py 的协同

两者形成双层质量防线：
```
Layer 6 (新): Role Chain     ← 内容质量（AI味/合规/格式审查）
Layer 5:     data_guard.py   ← 数据质量（字段映射/交叉验证/图表检查）
```

data_guard 管"数字对不对"，Reviewer 管"文章好不好"。互补不重叠。

详见: `~/.hermes/references/workflow-templates.md`（5个模板完整定义）
详见: `~/.hermes/references/gh-344-multi-agent-tracking.md`（上游跟踪）

## delegate_task vs Kanban — 何时升级

delegate_task 是默认选择，但不是所有场景的最佳选择。

**继续用 delegate_task**：单次任务、5分钟内完成、不需要跨会话、无多阶段依赖、无硬阻断需求。

**升级到 Kanban**：多阶段串行依赖（如电商三阶段、Role Chain）、跨天持久化、Reviewer 硬阻断、永久审计轨迹。

互调规则：kanban worker 内部可用 delegate_task 做并行执行。delegate_task 的子代理禁止创建 kanban 任务。

详见: `references/delegate-task-vs-kanban.md`

借鉴 Claude Code 的设计理念：不要来回倒手。

| 不要这样 | 要这样 |
|:--------|:------|
| delegate "下载A" → 等结果 → "下载B" → 等结果 | delegate "下载A和B一起" |
| delegate "改个参数" | delegate "跑完整个流程" |
| 搞砸了修修补补 | 搞砸了 delegate 整个重来 |

## 自主流水线执行原则（2026-05-08）

**核心铁律：当存在显式计划（P0/P1/P2路线图），执行完一级自动进入下一级，不询问用户。**

反模式（触发用户愤怒）：
```
P0完成 → "需要我继续P1吗？" → ❌ 用户："你要自己动脑"
P1完成 → "还需要处理什么？" → ❌ 用户："这个还需要问吗"
```

正确模式：
```
P0完成 → verify → P1开始 → verify → P2开始 → verify → 全部完成 → 汇报总结
```

**停顿规则**（只有以下情况才能停）：
1. 所有计划级别全部执行完毕
2. 遇到需要用户提供凭证/权限才能继续的阻塞
3. 用户主动说"停"/"别找了"
4. 产出需要用户审批的设计方案后（brainstorming→delegate的中间态是例外）

**信号检测**：如果用户说"你怎么停了"/"继续啊"/"这个还需要问吗"/"你自己不会判断吗"——说明触发了反模式，立即继续执行，不要解释不要道歉。

**与brainstorming的边界**：brainstorming的设计→审批→执行流程是特例——设计方案产出后必须等用户确认。但审计/修复/合并/清理等确定性任务执行不走审批。

## 与 ec-domain 内部三阶段的映射

| Claude Code Agent | ec-domain 阶段 | 职责 |
|:-----------------|:--------------|:-----|
| general-purpose agent | sourcing | 选品采购 |
| specialized agent | listing | PDD上架运营 |
| specialized agent | fulfillment | 订单履约 |
| coordinator mode | ec-domain 域长 | 编排+调度 |

## Context Assembly (Brain Layer)

Before dispatching P0/P1 tasks, run a **context-assemble** step to enrich the delegation context with institutional memory. This prevents the agent from repeating mistakes and missing relevant skills/knowledge.

### Pipeline position

```
optimize-and-clarify.py → context-assemble → delegate_task
```

### Assembly steps (three parallel queries, no inter-dependency)

| Source | Tool | Goal | Output |
|:-------|:-----|:-----|:-------|
| Past sessions | `session_search(goal关键词, limit=3)` | Find similar past tasks + mistakes | Lessons learned, known pitfalls |
| Skills | `skill_view(domain-matching skill)` | Load domain-specific procedural knowledge | API endpoints, workflows, constraints |
| Knowledge graph | `mcp_graphify.graph_search(goal关键词)` | Find related nodes from wiki/brain | Cross-references, dependencies |

### Assembly rules

1. **P0/P1 → mandatory**: Always assemble before delegation
2. **P2 → skip**: Low-stakes tasks don't need historical context
3. **Format**: Inject assembled findings into delegate_task's `context` field as a `[来自brain]` block
4. **Parallel**: Run all three queries simultaneously (they share no dependencies)

### Example enriched context

```
已知问题:K线parquet日期列类型不统一
[来自brain] 上次修复日期类型时用astype(str)统一
[来自brain] systematic-debugging技能: 4阶段根因调试流程
[来自brain] 知识图谱中发现3个相关节点: precache_kline.py, signal_engine.py, daily_signal_report.py
```

### Why this matters

Without context-assemble, the agent delegates "blind" — no awareness of past failures, no loaded skills, no knowledge graph connections. This causes:
- Repeating known mistakes (session_search missed)
- Missing domain-specific workflows (skill_view skipped)
- No cross-domain awareness (graph_search unused)

The brain layer turns delegation from "dump memory" to "compute what's relevant" (Anthropic's context engineering principle).

- Claude Code: AgentTool, forkSubagent, coordinatorMode
- Hermes: delegate_task API
- 本协议已内置到纯调度模式的系统规则中

## 与 Kanban 架构共存 (2026-05-11 审计结论)

在纯kanban路由模式下，delegate_task **不出现在总指挥的工具集中**。总指挥只使用 kanban_create/show/comment/block。delegate_task 降级为 kanban worker 的内部工具：

```
总指挥(路由器) → kanban_create → dispatcher → worker(内部可调delegate_task)
                                                    ↑
                                          delegate_task只在这里出现
```

本协议中定义的委托模式（单任务/并行批处理/流水线/编排器）仍适用于 kanban worker 内部。worker 在需要复杂多步推理时调用 delegate_task。

硬约束：
- ✅ kanban worker → delegate_task（允许，worker内部并行执行）
- ❌ delegate_task子代理 → kanban_create（禁止，无限嵌套风险）
- ❌ 总指挥 → delegate_task（禁止，kanban模式下总指挥只用kanban工具）

### kanban替代的机制

| 本协议定义的机制 | kanban替代方式 | 状态 |
|:--|:--|:--|
| Role Chain (role_chain.py) | parents依赖图 + reviewer worker | ✅ 废弃脚本 |
| quality_score.py | reviewer worker metadata | ✅ 废弃脚本 |
| pipeline_checkpoint.py | kanban SQLite持久化 | ✅ 废弃脚本 |
| Context Assembly (brain layer) | 总指挥用hindsight_recall + memory → 注入kanban body | ✅ 保留模式 |
| 模型选择策略 | 每个worker profile独立配置模型 | ✅ 更精细 |

### 参考文件

- `references/delegate-task-vs-kanban.md` — 完整决策指南 + 迁移手册
- `references/hindsight-fix-procedure.md` — Hindsight修复程序（kanban中用于上下文装配）
- `references/workflow-templates.md` — 工作流模板

---

- Claude Code: AgentTool, forkSubagent, coordinatorMode
- Hermes: delegate_task API（kanban架构中降级为worker内部工具）
- 本协议已内置到纯调度模式的系统规则中
