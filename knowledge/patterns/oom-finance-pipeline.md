# P002: 量化回测 OOM — 全量回测触发系统内存杀手

**出现次数**: 1 (但高风险)
**跨域**: finance-domain
**首次发现**: 2026-05-11
**严重度**: 🔴 CRITICAL

## 特征

1. signal_engine 一次加载 4000+ 只股票的全市场数据
2. 内存使用超系统上限
3. 系统 OOM killer 发送 signal 9 强制终止进程
4. 任务被 kill，数据丢失，需手动回收

## 实例

### 全量回测 (t_40062157)
- 日期: 2026-05-11 20:35-21:26
- 规模: 4939 只股票全量回测
- 结果: OOM kill (signal 9)
- 触发: 系统级内存不足

## 根因

- signal_engine 设计为一次性加载全部数据到内存
- 无分批机制
- 无内存预估
- 无 `max_runtime_seconds` / 内存限制配置

## 修复

1. **分批回测**: 每批 ≤500 只
2. **内存预估**: Worker 启动前 `len(stocks) × 估算 → 超 1GB 自动分批`
3. **运行时限制**: 配置 `max_runtime_seconds` + 内存限制
4. **渐进式加载**: 使用 generator/streaming 替代全量加载

## 关联

- [P003: 盲重试循环](blind-retry-cycles.md) — 同一管线的两个相关故障模式
- [finance-domain.md](~/.hermes/lessons/finance-domain.md) — "全量回测 OOM 风险"
