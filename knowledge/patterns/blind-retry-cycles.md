# P003: 盲重试循环 — Worker 崩溃无诊断信息导致无限重试

**出现次数**: 2+ (finance-domain ×1, stock-sdk MCP ×1)
**跨域**: finance-domain, code-domain
**首次发现**: 2026-05-11
**严重度**: 🔴 CRITICAL

## 特征

1. Worker 崩溃但仅返回 "exited with code 1"（无诊断信息）
2. Dispatcher 无熔断保护，盲目重试
3. 连续重试 7 次仍无成功
4. 下游依赖任务被级联阻塞

## 实例

### P2 因子计算 (t_0ebd895a)
- 日期: 2026-05-11 16:19-18:32
- 连续 crash: 7 次
- 错误信息: `""` (空)
- 第 8 次重试成功
- 影响: P3 信号扫描 (t_d5a748b4) 在此期间被级联阻塞 2 次

### stock-sdk MCP 非交易日空数据
- 日期: 2026-05-11 09:04-09:08
- 3 次触发 (code-domain ×2, finance-domain ×1)
- 根因: 非交易日返回空列表 → 下游除零崩溃

## 根因

1. **Worker 不产出诊断信息**: stdout/stderr 未捕获
2. **Dispatcher 无熔断**: 连续 crash 无退避，无上限
3. **下游无防御**: 依赖任务在父任务 crash 期间反复尝试

## 修复

1. **Worker 必须产出错误信息**: 捕获 stdout+stderr，写入 task_runs.error
2. **Dispatcher 熔断**: 连续 3 次 crash → 指数退避 (30s→60s→120s) + QQ Bot 告警 + 暂停下游
3. **下游防御**: 父任务 crash 期间不重试，等待父任务恢复
4. **空数据防御**: 调用前检查交易日 + `len(data)==0 → early return`

## 关联

- [P002: 量化回测 OOM](oom-finance-pipeline.md) — 同一 finance 管线的相关故障
- [finance-domain.md](~/.hermes/lessons/finance-domain.md) — "Pipeline Worker 盲重试循环"
- [global.md](~/.hermes/lessons/global.md) — "Kanban Worker 盲重试熔断"
