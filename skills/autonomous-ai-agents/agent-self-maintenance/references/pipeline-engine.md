# Cron Pipeline Engine — 长跨度任务执行机制

## 问题

长跨度任务（跨3天以上、中间被20条新指令打断）无法靠"中断恢复"解决。checkpoint 只保存事实，不恢复上下文状态感。每次新会话冷启动成本高（重读代码、重建理解）。

## 方案

不依赖会话连续性。将长任务拆为 self-contained 阶段，由 cron 独立执行。

```
用户说"做XXX"
  → 设计 pipeline（stage1 → stage2 → ... → stageN）
  → 每个 stage 是独立脚本（自包含、幂等、可验证）
  → 定义 pipeline → cron 每30分钟 tick 自动推进
  → 用户在任何时候发新指令 → pipeline 在 cron 里不受影响
  → L3 决策点 → pause → agenda 显示"等待决策"
  → 用户决策 → resume → pipeline 继续
  → 完成 → agenda 消失
```

## 架构

### 数据结构: pipelines.json

```json
{
  "pipelines": [
    {
      "id": "pipe-signal-decouple",
      "goal": "signal_engine 接口解耦",
      "stages": [
        {"id": 1, "desc": "提取 Protocol", "script": "...", "verify": "file exists:/path", "level": "L1", "completed_at": "..."},
        {"id": 2, "desc": "改 import", "script": "...", "verify": "", "level": "L1"},
        {"id": 3, "desc": "L3决策", "level": "L3"}
      ],
      "current": 1,
      "status": "running",
      "retries": {},
      "last_error": null
    }
  ],
  "last_tick": "2026-05-08 23:45"
}
```

### Stage 执行引擎: pipeline_runner.py

位于 ~/.hermes/scripts/pipeline_runner.py，cron fc7f76d16dd3 每30分钟 tick。

| 命令 | 作用 |
|:--|:--|
| `tick` | cron 调用，推进所有活跃 pipeline |
| `status` | 查看所有 pipeline 状态和当前 stage |
| `resume <id>` | 恢复暂停的 pipeline（L3 决策后调用） |
| `define` | 从 JSON 定义新 pipeline |

### WAIT Stage 类型 (v2.6)

用于需要**等待一段时间**后再继续的 pipeline。无脚本，只有 `until` 条件。

```json
{"desc": "观察 data_guard 稳定性 (7天)", "level": "WAIT", "until": "7d"}
{"desc": "等待IP白名单评估日", "level": "WAIT", "until": "2026-06-07"}
```

支持格式:
- 相对: `"7d"` = 7天后, `"30d"` = 30天后
- 绝对: `"2026-06-07"` = 到该日期, `"2026-06-07T00:00"` = 到该时刻

行为:
- pipeline 保持 `running` 状态（不是 `paused`）
- 每次 tick 检查时间: 未到期 → silent skip; 已到期 → 自动推进到下一 stage
- 不通知用户（WAIT 本身不需要决策，到期后的验证脚本出结果才通知）

### L3 决策流

```
pipeline 到达 L3 stage
  → status=paused, waiting_since 记录
  → notify_user() 写入 task_tracker.json
  → 下次会话启动协议读取 pipelines.json → "Pipeline X 在 stage N 等待决策"
  → 用户决策 → orchestrator 调用 resume <id>
  → resume 把 status 改回 running
  → tick 发现 running + 无脚本 L3 → 自动推进到下一 stage
  → 如果该 L3 是最后一 stage → pipeline completed
```

## Real-world Test Results (2026-05-08)

### Test 1: signal_engine ↔ chan_buy_signal 接口解耦

Pipeline: pipe-signal-decouple (4 stages)

| Stage | Level | Result |
|:--|:--|:--|
| 1. 提取 Protocol 契约 | L1 | 自动完成. 创建 chan_buy_contract.py |
| 2. 改 import 路径 | L1 | 自动完成. 幂等跳过 |
| 3. 隔离验证 | L2 | signal_engine 通过契约层加载 |
| 4. 清理决策 (L3) | L3 | paused->resumed->completed |

### Test 2: 共享工具函数合并

Pipeline: pipe-consolidate-utils (3 stages)

| Stage | Level | Result |
|:--|:--|:--|
| 1. 创建 shared_utils.py | L1 | safe_float + scrub_ai |
| 2. 改7脚本本地定义→共享import | L1 | 10处修改 |
| 3. 验证 | L1 | 无本地定义残留 |

## Stage 脚本编写规范

每个 stage 脚本必须：
1. **幂等** — 多次执行结果相同。用 if changes > 0 检测
2. **自包含** — 不依赖会话记忆。路径/配置硬编码
3. **可验证** — exit 0 = 成功
4. **短 timeout** — 默认 300s

### L3 决策通知链（QQ Bot 送达）

当 pipeline 遇到 L3 决策点时，用户需要即时收到通知，不能等 agenda（每天0点生成）或下次会话。

通知链：
```
pipeline tick → L3 stage 到达
  → tick() 调用 notify_user("Pipeline X 到 stage N，等待决策")
  → notify_user() 写入 task_tracker.json（agenda 次日显示）
  → 写入 .pipeline_notify 去重文件（同一条不重复推送）
  → print 到 stdout
  → cron deliver=qqbot 拾取 stdout → 投递到 QQ Bot（即时）
```

去重机制：`.pipeline_notify` 记录最后一条通知的 hash。连续两次 tick 触发同一条通知 → 第一次发出去，第二次 silent skip。

cron 配置（2026-05-09 更新）：`deliver: qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12`，每30分钟检查一次。平时安静（无事件不输出），有变化才响。

### WAIT Stage 类型（v2.6）

用于需要**等待一段时间**后再继续的 pipeline。无脚本，只有 `until` 条件。

```json
{"desc": "观察 data_guard 稳定性 (7天)", "level": "WAIT", "until": "7d"}
{"desc": "等待IP白名单评估日", "level": "WAIT", "until": "2026-06-07"}
```

支持格式:
- 相对: `"7d"` = 7天后, `"30d"` = 30天后
- 绝对: `"2026-06-07"` = 到该日期, `"2026-06-07T00:00"` = 到该时刻

行为:
- pipeline 保持 `running` 状态（不是 `paused`）
- 每次 tick 检查时间: 未到期 → silent skip; 已到期 → 自动推进到下一 stage
- 不通知用户（WAIT 本身不需要决策，到期后的验证脚本出结果才通知）
- 实现: pipeline_runner.py 中 `if now >= target → advance` 逻辑

### 使用 pipeline_runner.py 定义 pipeline

```bash
# 在会话中定义（推荐）
python3 -c "
import sys; sys.path.insert(0, '/home/pebynn/.hermes/scripts')
from pipeline_runner import define
define('目标描述', stages_list, 'pipeline-id')
"

# 查看状态
python3 ~/.hermes/scripts/pipeline_runner.py status

# 恢复暂停的 pipeline
python3 ~/.hermes/scripts/pipeline_runner.py resume <id>
```

### 实际测试结果（2026-05-08/09）

2026-05-08 全流程端到端验证:

**Test 3: data_guard 强制化（审计→构建→集成→观察）**

Pipeline: pipe-data-guard (6 stages)

| Stage | Result |
|:--|:--|
| 1. 审计35文件95处API调用 | 自动完成, audit report → /tmp/data_guard_audit.json |
| 2. 构建 data_guard v1 (145行, 5值域规则, 3入口函数) | 自动完成 |
| 3. 改collect_data + generate_charts 经过 guard | 自动完成 |
| 4. WAIT 7d 观察期 | 等待中 (2026-05-16 到期) |
| 5. 验证: 日志检查 | pending |
| 6. L3: 是否删旧直调路径 | pending |

**Test 4: 5条时间验证 pipeline 并行**

| Pipeline | WAIT 到 | 状态 |
|:--|:--|:--|
| pipe-stock-sdk-verify: 早报3交易日验证 | 2026-05-13 | ▶️ WAIT |
| pipe-noon-report-trigger: P0稳定→触发午评 | 2026-05-15 | ▶️ WAIT |
| pipe-ip-whitelist: IP变更频率评估 | 2026-06-07 | ▶️ WAIT |
| pipe-kline-integrity: K线缓存每周五检查 | 每周五 | ⏸️ L3 |
| pipe-morning-brief-sdk: stock_sdk适配确认 | 瞬时 | ⏸️ L3 |

## 已知限制

1. Stage 脚本必须 self-contained — 不能依赖 orchestrator 的代码理解
2. 跨 stage 数据传递通过文件系统
3. Shell escaping: 含中文/emoji/JSON 的 inline shell 命令会断。用独立 .py 文件
4. Virtualenv: 需要 pandas 的脚本必须用 quant_env 或显式 shebang
