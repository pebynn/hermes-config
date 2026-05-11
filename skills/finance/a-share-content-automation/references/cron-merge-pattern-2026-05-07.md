# Cron合并模式记录 (2026-05-07)

## 背景

writing-domain 有两个 08:00 cron 同时触发：
- 8dc31c90bf0d：盘前早报（no_agent脚本）
- 68dd0fd4adfe：早间巡检+信号（agent cron）

两个 cron 在同一分钟发送 weixin 消息 → iLink 并发限频（errcode=-2）→ 重试耗尽 → 报错 → 自动暂停。

## 解决方案

### 合并为一个 agent cron

将 8dc31c90bf0d 从 no_agent 转为 agent cron，合并三个任务为一条 weixin 消息：

```
8dc31c90bf0d「早间合并：盘前早报+巡检+信号」
  步骤1: morning_brief.py --no-push（生成早报文件，不推微信）
  步骤2: 系统健康（磁盘/内存/网关/雪球API 终端命令）
  步骤3: signal_engine 信号Top8
  步骤4: 汇总为一条消息 → weixin 推送
```

删除 68dd0fd4adfe。

### 同时恢复晚间 cron

b60f3c86dd1b（21:00 回测+信号）之前也被暂停，原因是当时 08:00 双并发 + 其他 cron 累积触发限频。合并 08:00 后恢复。

## 关键教训

- iLink 限频非"1h 冷却"，而是每次发送时服务端判断
- ercode=-2 → gateway 自动 3x 退避重试（~15s），重试耗尽才报错
- 根因是**同时段并发**，不是总量问题
- 工作日 5 条 weixin（08:00/09:55/16:00/18:00/21:00）无并发冲突，完全安全

## 当前 cron 布局

| 时间 | 任务 | deliver | 状态 |
|------|------|---------|------|
| 08:00 | 早报+巡检+信号 | weixin | ✅ |
| 09:55 | GLM抢购 | weixin | ✅ |
| 16:00 | 每日复盘 | weixin | ✅ |
| 18:00 | 复盘提醒 | weixin | ✅ |
| 21:00 | 回测+信号 | weixin | ✅ |
