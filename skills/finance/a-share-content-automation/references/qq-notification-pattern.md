# QQ通知共享模块 — 统一入口 + 审计结果

## 系统模块

**唯一入口**: `~/.hermes/scripts/notify.py`

**Skill**: `hermes-notify` (`~/.hermes/skills/hermes-notify/SKILL.md`)

## 使用方式

```python
import sys
sys.path.insert(0, '/home/pebynn/.hermes/scripts')
from notify import send as notify_qq

# 文章推送成功通知
notify_qq(title, "ok", f"{len(content)}字 | 每日复盘")
```

## 已接入脚本 (2026-05-10 审计)

| 脚本 | 调用次数 | 通知时机 |
|:--|:--|:--|
| generate_review_seo.py | 2 | 草稿箱推送成功 / publish_draft缺失 |
| generate_popular.py | 1 | 文章完成 |
| weekly_summary.py | 1 | 发布脚本成功 |
| quant_weekly.py | 1 | 推送完成 |
| weekend_deep_dive.py | 1 | 文章完成 |
| morning_brief.py | 1 | 早报完成 |

## 模块复用铁律

❌ 不要再创建新的通知模块 — `notify.py` 是唯一入口
❌ 不要用 print() 替代 QQ 通知
❌ 不要绕过此模块直接调用 QQ Bot API
❌ 先查后建 — 新增功能前 grep -r 搜索现有实现
