# QQ通知架构 (2026-05-11)

## 统一通知模块

`~/.hermes/scripts/notify.py` — 所有 writing-domain 脚本的唯一 QQ Bot 通知入口。

### 调用方式

```python
from notify import send, article_published

# 通用
send("标题", "正文", priority="P1")

# 文章发布
article_published("每日复盘", date_str)
article_published("周总结", date_str, "3200字")
article_published("科普", date_str, title)
article_published("早报", date_str)
article_published("短内容", date_str, "4条")
```

### 投递流程

1. 脚本调用 notify.send() → 写入 JSON 到 `~/.hermes/notify_queue/{timestamp}.json`
2. pipeline_runner cron (fc7f76d16dd3, 每30min) 扫描队列
3. `deliver_queued_notifications()` 读取 JSON → stdout 输出
4. cron deliver(qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12) 拾取 stdout → QQ Bot

### 已接入脚本 (2026-05-11)

| 脚本 | 通知触发点 | 通知内容 |
|:--|:--|:--|
| generate_review_seo.py | publish_draft.py 返回成功 | "📊 每日复盘已生成" |
| weekly_summary.py | 草稿保存+data_guard通过后 | "📈 周总结已生成" |
| morning_brief.py | push_to_wechat() 后 | "🌅 早报已生成" |
| generate_popular.py | push_draft() 成功后 | "📖 科普已生成" |
| generate_short_posts.py | publish_draft.py 返回成功 | "📱 短内容已生成" |

quant_weekly.py 除外（用户要求独立处理，走 cron deliver 原生通道）。

### 禁忌

- ❌ 禁止各脚本自行实现 QQ 通知（import requests 调 webhook 等）
- ❌ 禁止使用 PushPlus/Server酱/iLink
- ❌ 禁在 notify.py 中硬编码 token
- notify.py 的文件队列机制是唯一通道，不要绕过
