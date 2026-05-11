# 每日教训审计报告 — 2026-05-09

**生成时间**: 2026-05-09 22:00 CST  
**审计类型**: 自动 cron 扫描  

---

## 🔴 新发现 CRITICAL 教训

### GLM API Token 过期导致全系统级联故障 (→ ops-domain)

| 属性 | 值 |
|:--|:--|
| 首次发现 | 2026-05-08 17:21 |
| 今日发生 | 5+ 次 (18:10, 18:12, 18:40) |
| 严重度 | 🔴 CRITICAL |
| 影响范围 | ops-domain, writing-domain, finance-domain, 所有 cron |

**故障链**:
```
GLM API Token 过期 (401 — 令牌已过期或验证不正确)
  ├─ title_generator 标题生成失败 (3次)
  ├─ session_summarizer 会话摘要失败 (2次)
  ├─ cron: graphify-daily 失败
  ├─ cron: circuit-guard-hourly 失败
  ├─ cron: 每日K线更新 失败
  ├─ cron: A股每日复盘生成+发布 失败
  └─ 活跃 session LLM 调用失败 (多个 session)
```

**检测方法**: `grep "401.*令牌已过期" ~/.hermes/logs/errors.log`  
**修复**: 更新 API key/token → 重启 gateway  
**预防**: 
1. Token 过期前 7 天预警
2. Token 轮换后自动验证所有 cron job 可用性
3. Token 健康检查集成到 circuit-guard 每小时检查中

✅ **已添加到 lessons** -> `~/.hermes/lessons/ops-domain.md`

---

## 🟠 持续活跃的已知教训

### QQBot WebSocket 持续快速重连循环
- **今日**: 663 次 "WebSocket error: WebSocket closed" + 17 次 "Session timed out" = **680 次**
- **周期**: ~62s/次，全天持续
- **已记录**: 2026-05-08 audit → ops-domain.md 🟠 HIGH

### GLM API 401 Token 过期（跨域蔓延）
- **跨 2 天**: 2026-05-08 (17:21 起) → 2026-05-09 (持续)
- **总计**: 20+ 次，涉及 4+ cron job、5+ session
- **已升格**: 今日从发现升格为 🔴 CRITICAL lesson

---

## 🟡 一次性/低频率事件

| 事件 | 次数 | 时间 | 判断 |
|:--|:--|:--|:--|
| MCP 全集群 CancelledError | 17 server × 5 次 | 02:09 | Gateway 重启期间的瞬态故障，无需独立 lesson |
| CDP browser_tool 端点不可用 | 88 | 02:09 + 18:38 | localhost:9377 无浏览器进程，已知问题 |
| Weixin rate limiting (o9cq803I) | 16 WARN + 4 ERROR | 02:13 | 正常限频回退，单用户 |
| asyncio shutdown 异常 | 3 Unclosed + 2 unhandled | 02:09-02:14 | Gateway 关闭竞态，低优先级 |

---

## ⚙️ Circuit Guard 状态

| 指标 | 值 |
|:--|:--|
| 状态 | ✅ OK |
| 活跃模型 | glm-5.1 |
| 失败计数 | 0 |
| 熔断阈值 | 5次/30min |
| 24h 费用 | $0.00 |
| 总 session | 2 |

**无 circuit breaker 触发，无需通知。**

---

## 📊 今日统计

| 类别 | 数量 |
|:--|:--|
| 新 CRITICAL 教训 | 1 |
| 已知教训持续 | 2 |
| 低频事件 | 4 |
| Circuit breaker 触发 | 0 |
| 系统总体状态 | 🟡 降级运行（token 过期影响所有 cron） |

---

## 🔧 建议后续动作

| # | 动作 | 优先级 |
|:--|:--|:--|
| 1 | 更新 GLM API token 并重启 gateway | 🔴 立即 |
| 2 | Token 更新后验证所有 cron job 恢复 | 🔴 立即 |
| 3 | 添加 token 过期预警到 circuit-guard | 🟠 本周 |
| 4 | 评估 QQBot 是否需要关闭适配器（2天持续断连） | 🟡 评估 |
