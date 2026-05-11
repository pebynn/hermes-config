# Pipeline 引擎 — 长跨度任务执行器

替代 checkpoint 方案（checkpoint 只解决中断恢复，不解决跨会话持续执行）。

## 核心文件

| 路径 | 作用 |
|:--|:--|
| `~/.hermes/scripts/pipeline_runner.py` | 引擎：tick/status/resume/define |
| `~/.hermes/agenda/pipelines.json` | 所有 pipeline 状态持久化 |
| cron `fc7f76d16dd3` `*/30 * * * *` | 每30分钟自动 tick |

## 阶段类型

| Level | 行为 | 示例 |
|:--|:--|:--|
| L1 | 自动执行脚本 → 验证 → 推进 | `script: 'python3 stage1.py'` |
| L2 | 同L1，简报用户 | 同上 |
| L3 | 无script → 暂停 → 通知用户决策 | `script: '', level: 'L3'` |
| WAIT | 无script → 等到 until 时间 → 自动推进 | `level: 'WAIT', until: '7d'` 或 `until: '2026-06-07'` |

## 常用命令

```
pipeline_runner.py status            # 查看所有 pipeline
pipeline_runner.py tick              # cron 调用：推进一次
pipeline_runner.py resume <id>       # 恢复暂停的 pipeline
```

## WAIT 时间格式

- 相对: `'7d'` → 7天后
- 绝对: `'2026-06-07'` → 指定日期
- 精确: `'2026-06-07T00:00'` → 指定日期时间

## 定义 pipeline

```python
from pipeline_runner import define
define('任务描述', [
    {'id': 1, 'desc': '步骤1', 'script': '...', 'level': 'L1', 'verify': 'file exists:...'},
    {'id': 2, 'desc': '等待观察', 'level': 'WAIT', 'until': '7d'},
    {'id': 3, 'desc': '验证', 'script': '...', 'level': 'L1'},
    {'id': 4, 'desc': '决策点', 'level': 'L3'},
], 'pipe-task-id')
```

## 通知机制

- L3 暂停 → `notify_user()` 打印到 stdout
- cron deliver 拾取 stdout → 投递到 QQ Bot
- 重复通知自动去重
- 同时写入 task_tracker.json → aagenda 次日显示
