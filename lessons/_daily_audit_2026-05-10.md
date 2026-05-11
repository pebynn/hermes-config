# 每日教训审计 — 2026-05-10

**执行时间**: 2026-05-10 22:00 UTC
**状态**: ✅ 完成

---

## 1. 域教训注入测试

| 域 | 结果 |
|:--|:--|
| writing-domain | ✅ 注入成功，返回 31 条已知教训 |

---

## 2. 今日 errors.log 分类统计

| 模式 | 出现次数 | 严重度 | 是否新增 |
|:--|--:|:--|:--|
| QQBot WebSocket 断开 | ~1400 | WARNING | ❌ 已知 |
| Hindsight retain 失败 (aretain_batch) | 30 | WARNING | ✅ **新增** → 已加教训 |
| Session summarization 429 限流 | 103 | WARNING | ❌ 已知 (DeepSeek 抖动) |
| Browser CDP endpoint 不可达 | 289 | WARNING | ❌ 已知 (无 browser_tool) |
| Gateway 重复实例 | 4 | ERROR | ❌ 已知 |
| Git working directory 缺失 | 4 | ERROR | ⚠️ 偶发 |
| Weixin rate limited | 12 | WARNING/ERROR | ❌ 已知 |
| QQBot Session timed out | 4 | WARNING | ⚠️ 偶发 |

---

## 3. 新增教训

**域**: ops-domain | **级别**: HIGH
**标题**: Hindsight API 版本过旧导致批量记忆保留失败

**根因**: Hindsight API 版本 < 0.5.0，回退到 per-process document_id 模式，Embedded 客户端缺少 `aretain_batch`/`aretain` 方法。

**触发信号**: 日志中出现 `Hindsight retain failed: 'HindsightEmbedded' object has no attribute 'aretain_batch'`

**影响**: 所有跨 session 的 memory retain 操作静默失败，知识无法持久化。

**修复路径**:
1. 升级 Hindsight 到 0.5.0+: `pip install --upgrade hermes-hindsight`
2. 验证 `aretain_batch` 方法可用
3. 如无法升级，检查替代 retain 方案

---

## 4. Circuit Guard 状态

```json
{"status": "ok", "active_model": "deepseek-v4-pro", "fail_count": 0, "cost_24h": 0.0}
```

- 无熔断触发
- 当前活跃模型: deepseek-v4-pro
- 30分钟窗口内失败: 0/5

---

## 5. 持续关注项

| 项 | 状态 | 建议 |
|:--|:--|:--|
| QQBot WebSocket 持续断开 | 全天每秒2次 | 检查 QQBot 网关连接，考虑自动重连策略 |
| Session summarization 429 | 凌晨高峰 (00:36-02:05, 20:05) | 已由 circuit-guard 管理 |
| Browser CDP 不可达 | 频繁 | browser_tool 未安装/未启动，非紧急 |
| `/hermes/references` 目录缺失 | 4次 | 创建该目录或修复 checkpoint_manager 路径 |

---

## 6. 操作记录

- ✅ `lesson_inject.py inject --domain writing-domain` → 成功
- ✅ `lesson_inject.py add --domain ops-domain` → Hindsight 教训已添加
- ✅ `circuit-guard.py --json` → 正常
- ℹ️ 无 circuit breaker 触发，无需通知用户
