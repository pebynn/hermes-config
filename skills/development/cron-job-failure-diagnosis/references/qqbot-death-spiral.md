# QQ Bot WebSocket 断连风暴 — 诊断与修复

## 症状

Gateway日志出现密集的QQ Bot断连-重连循环：

```
01:09:17 WebSocket error: WebSocket closed
01:09:19 WebSocket connected → Resume sent → Session resumed
01:10:19 WebSocket error: WebSocket closed
01:10:21 WebSocket connected → Resume sent → Session resumed
...
```

模式：每 ~62 秒一次断连-重连循环，可持续 24h+。

## 影响

- **所有 `deliver: qqbot` 的 cron 推送全部丢失**
- 日志出现 `no delivery target resolved for deliver=origin`
- Cron 本身可能正常运行（`last_status: ok`），但产出静默丢弃
- 持续重连消耗 gateway 资源 → 连锁导致 kanban dispatcher 崩溃 → 系统重启
- 历史上曾导致 2026-05-12 全天推送丢失 + 11:49 系统重启

## 诊断

```bash
# 检测是否正在死亡螺旋（每62秒断连一次）
grep "QQBot.*WebSocket error: WebSocket closed" ~/.hermes/logs/gateway.log | tail -20

# 如果最近10条 closed 记录在10分钟内 → 确认死亡螺旋
grep "QQBot.*WebSocket error: WebSocket closed" ~/.hermes/logs/gateway.log | tail -10
```

**关键特征**：session_id相同，seq递增（resume成功），但60秒后被踢。

## 根因：Poisoned Session（毒化会话）

QQ Bot session 被毒化——每次 resume 被接受但 60 秒后被服务器主动踢断。

代码缺陷在 `~/.hermes/hermes-agent/gateway/platforms/qqbot/adapter.py`：

1. `_read_events()` 第 645 行：无 close code 的断连（`WSMsgType.CLOSED/ERROR`）抛出 `RuntimeError("WebSocket closed")`
2. `_listen_loop()` 第 589 行：通用 `except Exception` 捕获后调用 `_reconnect()` —— **不清除 session_id**
3. `_reconnect()` 重新打开 WebSocket，Hello 到达后检查 `self._session_id` 非空 → **Resume 毒化 session**
4. QQ 服务器接受 Resume → 60 秒后踢断 → 回到步骤 1

强 code（4009/4006 等）走 `QQCloseError` 分支会正常清 session，但无 code 断连永远不清 → 无限循环。

## 修复（已应用，2026-05-13）

修改 `adapter.py` `_listen_loop()` 方法：

1. 新增 `no_code_disconnect_count` 计数器
2. 第 589 行异常处理器中检测 `RuntimeError("WebSocket closed")`：
   - 计数器 +1
   - 连续 2 次 → 清 `self._session_id = None` + `self._last_seq = None` → 日志 "Clearing poisoned session, will re-identify"
3. 下次 `_reconnect()` 时 `_session_id` 为空 → Hello 后走 **Identify**（新 session）而非 Resume

```python
# 核心修复逻辑 (adapter.py _listen_loop)
if isinstance(exc, RuntimeError) and "WebSocket closed" in str(exc):
    no_code_disconnect_count += 1
    if no_code_disconnect_count >= 2:
        self._session_id = None   # 清毒session
        self._last_seq = None     # 强制re-identify
```

## 验证

修复后网关日志应出现：
```
WebSocket error: WebSocket closed    ← 毒session被踢
No-close-code disconnect #1
WebSocket error: WebSocket closed    ← 再次被踢
No-close-code disconnect #2
Clearing poisoned session, will re-identify
Identify sent                        ← 新session
Ready, session_id=<NEW_ID>           ← 全新session，不会再60秒被踢
```

此后不应再出现每 60 秒的断连循环。
