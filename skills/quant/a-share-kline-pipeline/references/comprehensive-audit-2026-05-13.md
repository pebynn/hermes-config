# K线采集管线全面审计 — 2026-05-13

## 发现的问题

### 1. K线更新cron超时 (P0 ✅已修复)

**症状**: `afff56398abe` (每日K线更新 16:00 Mon-Fri) last_status=error
**根因**: hermes cron runner对no_agent脚本有**独立120s硬超时**，与.env TERMINAL_TIMEOUT=600无关
**证据**: 输出文件 `Script timed out after 120s`，手动跑64s成功
**修复**: 
- 重写 `~/.hermes/scripts/daily_kline_update.sh`：exec直调Python，减少shell套层开销
- 64s完成验证通过（4934 stocks，tushare 0.7s + 63s写parquet/MySQL）

### 2. 三策略信号cron脚本路径错误 (P0 ✅已修复)

**症状**: `0637e225e375` (16:10 Mon-Fri) Script not found
**根因**: cron `script` 字段解析到 `~/.hermes/scripts/`，而非任务工作目录
**实际位置**: `~/quant/run_daily_signals.sh`
**修复**: 创建 `~/.hermes/scripts/run_daily_signals.sh` wrapper → `/bin/bash ~/quant/run_daily_signals.sh`
**验证**: 手动运行成功（A:5 B:12 C:8 signals，112.5s）

### 3. MCP进程严重增殖 (P0 ✅已修复)

**症状**: 9个MCP服务器各有5个进程，总计45个僵尸进程
**根因**: Gateway多次重启，旧进程未被kill
**修复**: 批量清理至每服务1进程
**命令**:
```bash
for srv in mcp-graphify mcp-mysql mcp-prompt-optimizer mcp-skill-auditor \
           mcp-deep-research mcp-web-search mcp-web-extract mcp-cost-guard \
           mcp-security-auditor mcp-llm-wiki; do
  count=$(ps aux | grep "${srv}.py" | grep -v grep | wc -l)
  if [ "$count" -gt 1 ]; then
    ps aux | grep "${srv}.py" | grep -v grep | sort -k10 | head -n $((count - 1)) | awk '{print $2}' | xargs kill
  fi
done
```

### 4. MySQL 5/13数据缺失 (P1 ✅已修复)

**症状**: cron失败导致当天K线未入库
**修复**: 手动运行 daily_kline_update.py → 4934 stocks写入MySQL

### 5. 信号文件0字节 (P1 ✅已修复)

**症状**: signals_2026-05-13.json 仅345字节，三策略0信号
**根因**: K线数据缺失→因子计算无输入
**修复**: K线回填后重新生成信号

### 6. 两融cron 5/13失败 (P2 ⚠️未修复)

**症状**: `18edaa02cd7e` last_status=error
**根因**: AKShare `stock_margin_detail_sse` 返回空DataFrame(0行)，pandas 3.x的columns赋值报 `ValueError: Length mismatch`
**影响**: 非交易日也有类似错误（数据延迟发布），影响小
**建议**: margin_data.py 增加空DataFrame保护 + 非交易日跳过

### 7. tushare stock_basic频率限制 (P2 ⚠️未修复)

**根因**: 实际限制1次/小时（非文档描述的1次/分钟）
**影响**: 首次调用后缓存7天，日常不影响

## Cron wrapper最佳实践

```bash
#!/bin/bash
# 关键：设置HOME + PATH + cd + exec直调Python
export HOME=/home/pebynn
export PATH="/home/pebynn/tools/quant_env/bin:/usr/local/bin:/usr/bin:/bin"
cd /home/pebynn/quant
exec /home/pebynn/tools/quant_env/bin/python3 /home/pebynn/quant/daily_kline_update.py
```

**原则**:
- `exec` 避免bash子进程残留
- 不在wrapper中做复杂逻辑（交易日检查等应在Python中）
- 所有cron wrapper统一放 `~/.hermes/scripts/`

## 架构风险

| 风险 | 说明 | 缓解 |
|:--|:-----|:-----|
| MCP增殖复发 | Gateway重启后僵尸进程累积 | 建议增加cron自动清理 |
| cron 120s硬限制 | no_agent脚本无法突破 | 保证脚本<100s |
| tushare超时 | 免费版~5-10%概率connection timeout | 手动重跑或分市场 |
| AKShare不稳定 | 两融/财务API偶发超时/空返回 | 非关键数据，容忍 |

## 数据流健康度 (修复后)

| 检查项 | 状态 | 数值 |
|:--|:--|:--|
| MySQL kline最新日期 | ✅ | 2026-05-13 |
| 当日stocks数 | ✅ | 4934 |
| parquet缓存数 | ✅ | 5514 |
| 当日信号 | ✅ | A:5 B:12 C:8 |
| 两融数据 | ❌ | 无 |
