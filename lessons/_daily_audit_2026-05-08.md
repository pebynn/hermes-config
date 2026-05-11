# 每日教训审计报告 — 2026-05-08

## 1. writing-domain 教训注入测试
✅ lesson_inject.py inject --domain writing-domain — 正常输出，7条🔴+7条🟠+4条🟡 教训加载正常

## 2. 今日失败模式扫描

### 🔴 CRITICAL — API Token 过期级联故障（新教训，已添加）
- **时间**: 17:21 CST 开始
- **数量**: 24次 401 Non-retryable client error
- **影响作业**: graphify-daily ❌ | circuit-guard-hourly ❌ | 每日K线更新 ❌ | A股每日复盘生成+发布 ❌
- **关联影响**: 5+ 会话全部因同一 token 过期失败
- **根因**: Hermes gateway API token 过期，无自动续期/告警机制
- **处理**: ✅ 已添加为 ops-domain CRITICAL 教训

### 🟠 HIGH — QQBot WebSocket 快速重连循环（新教训，已添加）
- **时间**: 20:37-21:37 CST（恶化阶段）
- **数量**: 117 次 WebSocket 相关错误 (40 timed out + 77 error)
- **模式**: 06:00-20:30 正常间歇性断连 → 20:37 后每~62s 重连失败
- **根因**: 可能与 API token 过期有关（WebSocket auth 被踢）
- **处理**: ✅ 已添加为 ops-domain HIGH 教训

### 🟡 MEDIUM — Vision API Key 失效
- **时间**: 18:10 / 20:01 CST
- **数量**: 3 次 Authentication Fails (key: ****2b57)
- **影响**: vision_tools 不可用
- **处理**: 非新模式（同一 token 过期问题的副产品），不单独加教训

### 🟢 DeepSeek 503 (1次)
- 单次 Service is too busy (17:25)，5次重试后失败
- 非新模式，已有 fallback 机制

### 🟢 Browser CDP 端口故障（157次）
- 非新模式，昨日已有 lesson: "Browser CDP 端口 9377 不可用"
- 持续性问题，未恶化

### 🟢 asyncio shutdown 告警
- "Task was destroyed but it is pending!" / "Task exception was never retrieved" x 434
- 均为正常进程关闭产物，无需处理

## 3. Circuit Guard 状态
✅ **HEALTHY**
- active_model: deepseek-v4-flash
- fail_count: 0 / 5 (threshold)
- cost_24h: $0.00
- 无熔断触发 → 无需通知

## 4. 新教训统计
| 域 | 级别 | 教训标题 |
|:--|:--|:--|
| ops-domain | 🔴 CRITICAL | API Token 过期→全部cron级联失败 |
| ops-domain | 🟠 HIGH | QQBot WebSocket 快速重连循环 |

## 5. 建议关注
1. **Token 续期**: 需立即检查 ~/.hermes/.env 中的 API token 是否已更新
2. **A股复盘**: 今日复盘生成+发布因 token 过期失败（17:35），需手动重跑
3. **QQBot**: 重连循环可能仍在持续，需重启 gateway 或检查 token
4. **监控短板**: 今日 token 过期后无任何自动告警，需补充 token 健康检查 cron
