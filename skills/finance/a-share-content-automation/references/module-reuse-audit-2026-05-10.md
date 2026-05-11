# 写作管线模块复用审计 (2026-05-10)

## 教训：先查后建，禁止重复造轮子

**反例**: `writing-data/scripts/shared/notify_utils.py` 重复实现了 QQ 通知功能，而 `~/.hermes/scripts/notify.py` 已有完整的优先级队列+重试+每日摘要系统。

**正确做法**:
1. 建任何模块前先搜 `~/.hermes/scripts/` 和 `~/writing-data/scripts/shared/`
2. 找到就用，不建新的
3. 建完立即注册 skill
4. 优先放 `~/.hermes/scripts/` 而非域子目录

## 已发现的重复

| 重复模块 | 系统模块 | 状态 |
|:--|:--|:--|
| `writing-data/scripts/shared/notify_utils.py` | `~/.hermes/scripts/notify.py` | ✅ 已删除 |
| `writing-data/shared/data_guard.py` (v1) | `writing-data/scripts/shared/data_guard.py` (v2) | ⚠️ 双版本，`collect_data.py`和`generate_charts.py`仍引用v1 |

## 6个写作脚本统一入口

全部6个脚本已统一使用：
```python
import sys
sys.path.insert(0, '/home/pebynn/.hermes/scripts')
from notify import send as notify_qq
```

禁止 `from shared.notify_utils import notify_qq` — 此模块已删除。

## 全局教训

见 `~/.hermes/lessons/global.md` CRITICAL 区 "模块复用铁律"。
