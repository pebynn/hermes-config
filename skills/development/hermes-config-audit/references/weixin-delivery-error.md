# WeChat 推送 Delivery Error — 根因与修复

## 错误签名

```
delivery error: Weixin send failed: Timeout context manager should be used inside a task
```

## 影响范围

- cron 任务本身成功（`last_status: ok`）
- 仅微信推送失败
- 同一 gateway 实例下所有微信 delivery cron 均受影响
- 实例：2026-05-04 审计发现 6/21 cron 有此错误

## 根因

Gateway 层 `gateway/platforms/weixin/adapter.py` 中 asyncio 任务上下文问题。
`send_message` 方法在非 asyncio task 上下文中使用了 `asyncio.timeout()`，
导致 `Timeout context manager should be used inside a task` 异常。

## 修复路径

### 方案 A: 升级 Hermes Agent（推荐）
```bash
cd ~/.hermes/hermes-agent
git pull origin main
source venv/bin/activate
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
systemctl --user restart hermes-gateway
```

### 方案 B: 手动 patch（如升级不可行）
在 `gateway/platforms/weixin/adapter.py` 的 `send_message` 方法中，
确保 `asyncio.timeout()` 调用在 `asyncio.create_task()` 或已在运行的 task 中。

## 检测命令

```bash
# 列出所有有此错误的 cron
cronjob list 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
for j in data.get('jobs', []):
    err = j.get('last_delivery_error', '')
    if 'Timeout context manager' in (err or ''):
        print(f\"{j['name']}: {err}\")
"
```

## 临时缓解

错误不影响任务执行，仅影响推送。如果推送不是刚需，可暂时忽略。
如需推送，临时方案：将 cron 的 `deliver` 改为 `local`，总指挥在会话中主动检查。
