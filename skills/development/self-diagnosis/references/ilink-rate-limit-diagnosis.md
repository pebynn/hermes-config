# iLink WeChat 限频诊断与修复

## 症状

`send_message` 返回 `ret=-2 rate limited`，且多次重试持续失败。

## 诊断路径

### 1. 确认限频来源（gateway.log vs errors.log）

```bash
# gateway.log 显示连接状态
grep -i 'weixin' ~/.hermes/logs/gateway.log | tail -20

# errors.log 显示实际投递失败，关键看 session_id
tail -20 ~/.hermes/logs/errors.log
```

关键判断：errors.log 中的 `[session_id]`（如 `[20260506_045552_a12590]`）揭示了哪个会话在消耗配额。

### 2. 判断是旧队列还是新投递

- 如果 session_id 的时间戳是过去的（如 `045552` 代表 04:55，但当前已 05:30）→ **旧session队列在重试**
- Gateway 重启后旧队列仍会重试，因为 cron job 的 delivery 是持久化的
- 旧队列的每次重试（含4次backoff）会刷新 iLink 冷却计时器

### 3. 冷却周期

iLink rate limit 冷却约 **1小时**，但每次新的 rate limited 响应会重置计时器。旧session如果持续重试，会形成"永远解不了"的死循环。

## 修复策略

### 短期：等冷却自然解除

如果 cron 已优化（不再有密集投递），等 ~1h 自动恢复。不要在冷却期反复测试——每次测试都会刷新计时器。

### 中期：cron 归并减少投递密度

参见本文档的 "Cron 归并模式" 章节。

### 长期：预防

- WeChat 投递 ≤5条/天，间隔 ≥2h
- session-watchdog、cost-report 等非紧急任务走 `deliver: local`
- 高频 cron（每30min/每小时）不投 weixin

## 典型故障时间线

```
04:12  session-watchdog 触限（旧 30min weixin 调度）
04:32  重试再次触限
04:50  session-watchdog 又一轮触限 → disconnect
04:54  gateway 自动重连
05:24  gateway 重启，但旧队列重试再次触限
05:25  旧 session [20260506_045552] 的4次重试全部失败
05:30-05:35  新 send_message 仍被限（冷却未过）
06:00  预计冷却解除
```

教训：清理 cron 后，旧队列可能还在消耗配额。不会立即生效，需等冷却周期过。
