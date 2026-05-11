---
name: hermes-notify
description: 统一QQ Bot通知模块 — 所有脚本的唯一通知入口
version: 1.0.0
---

# Hermes 通知模块

所有脚本/agent/cron 统一通过此模块发送 QQ Bot 通知。禁止各自实现通知逻辑。

## 架构

```
脚本/agent 调用 notify.send()
  → 写入 JSON 文件到 ~/.hermes/notify_queue/
  → pipeline_runner tick (每30min) 扫描队列
  → stdout 输出 → cron deliver 拾取 → QQ Bot
```

## Python API

```python
from notify import send, article_published

# 通用通知
send("标题", "正文", priority="P1")

# 文章发布通知（便捷函数）
article_published("每日复盘", "2026-05-11")
article_published("周总结", "2026-05-11", "3200字")
article_published("科普", "2026-05-11", "新手如何看K线")
article_published("早报", "2026-05-11")
article_published("短内容", "2026-05-11", "4条")
```

## Shell API

```bash
python3 ~/.hermes/scripts/notify.py "标题" "正文"
```

## 已接入脚本

| 脚本 | 触发点 |
|:--|:--|
| generate_review_seo.py | 草稿箱推送成功后 |
| weekly_summary.py | 周总结保存后 |
| morning_brief.py | 早报推送后 |
| generate_popular.py | 科普推送到草稿箱后 |
| generate_short_posts.py | 短内容推送后 |

quant_weekly.py 除外（用户要求独立处理）。

## 优先级

| 级别 | 含义 | 行为 |
|:--|:--|:--|
| P0 | 紧急 | 立即送达 |
| P1 | 重要 | 立即送达（默认） |
| P2 | 提示 | 队列投递 |
| P3 | 常规 | 仅每日摘要 |

## 投递机制

`pipeline_runner.py` 的 `deliver_queued_notifications()` 函数每30分钟扫描 `~/.hermes/notify_queue/*.json`，逐个输出到 stdout → cron deliver(qqbot) 拾取 → QQ Bot。投递后删除文件避免重复。

## 禁忌

- ❌ 禁止各脚本自行实现 QQ Bot 通知
- ❌ 禁止使用 PushPlus/Server酱/iLink 等其他通道
- ❌ 禁止在 notify.py 中硬编码 token/密钥
