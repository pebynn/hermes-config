# QQ Bot 投递连通性验证

## 验证流程

### 1. 检查 Gateway 日志

QQ Bot 通过 Hermes Gateway 的 WebSocket 连接到腾讯官方 API：

```bash
# 检查最近一次连接状态
grep 'QQBot.*Ready' ~/.hermes/logs/gateway.log | tail -1
# 期望: 2026-05-08 16:01:01,521 INFO [...] Ready, session_id=5b0188e5-...
```

### 2. 检查 WebSocket 稳定性

```bash
# 检查断线模式 — 只有 code=4009(session超时)是正常的
grep 'QQBot.*WebSocket closed' ~/.hermes/logs/gateway.log | tail -3
# 正常: code=4009 reason=Session timed out
# 异常: code=1006 (连接异常断开), code=400x 其他 (认证/权限问题)
```

### 3. 验证自动重连

QQ Bot 每 30 分钟 session 超时并自动重连：

```
WebSocket closed: code=4009 reason=Session timed out  ← 正常
Reconnecting in 2s (attempt 1)...
WebSocket connected to wss://api.sgroup.qq.com/websocket
Reconnected
Identify sent
Ready, session_id=...                                  ← 恢复
```

## 已知正常状态

| 指标 | 正常值 |
|------|--------|
| 重连间隔 | ~30min (腾讯端 session 超时) |
| 重连速度 | ~3秒 (2s延迟 + 1s握手) |
| API 端点 | wss://api.sgroup.qq.com/websocket |
| 机器人 ID | 1903877702 |

## 故障排查

### QQ Bot 完全没日志

```bash
systemctl --user status hermes-gateway.service     # gateway 在跑吗？
grep -i qqbot ~/.hermes/config.yaml                # platforms.qqbot 配置了吗？
grep -i qq ~/.hermes/.env                          # QQ_APP_ID / QQ_CLIENT_SECRET 存在吗？
```

### QQ Bot 反复断线连不上

```bash
grep 'QQBot.*WebSocket closed\|QQBot.*ERROR' ~/.hermes/logs/gateway.log | tail -10
# 常见 code 含义:
#   4009 — session 超时（正常，自动重连）
#   4010 — 心跳超时（网络抖动）
#   4001 — 认证失败（token 过期）
#   1006 — 连接异常断开（网络或腾讯端问题）
```

### token 过期

需要重新注册：`python3 ~/.hermes/scripts/setup_qqbot.py` 扫码获取新凭证。

## 投递目标格式

cron 投递目标统一使用：
```
qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12
```
注意这是 QQ Bot 的 bot ID，不是个人 QQ 号。
