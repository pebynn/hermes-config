# 三策略每日信号管线 — 配置现状 (2026-05-13)

## Cron 配置

| job_id | name | schedule | no_agent | script | last_status |
|--------|------|----------|----------|--------|-------------|
| `afff56398abe` | 每日K线更新 | 0 16 * * 1-5 | true | `daily_kline_update.sh` | error (5/13) |
| `1f0ac0e8a94e` | 三策略每日信号+QQ投递 | 10 16 * * 1-5 | true | `run_daily_signals.sh` | never run |

## 脚本依赖链

```
afff56398abe (16:00)             1f0ac0e8a94e (16:10)
  │                                │
  └─ daily_kline_update.sh        ├─ 交易日检查 (data_common.get_trading_calendar)
     └─ daily_kline_update.py     ├─ 数据入库检查 (kline表 >= 3000只, 等5次×2min)
        ├─ tushare pro.daily()    ├─ daily_signals.py → 空文件(0行) ❌
        ├─ 雪球 fallback          └─ send_signals_qq.py → 不存在 ❌
        └─ AKShare fallback
```

## 策略代码实际位置

memory 记录为 `strategy_momentum_evo/reversal/chan.py`，**实际文件**：

| 文件 | 路径 | 状态 |
|------|------|------|
| `strategy_momentum.py` | `/home/pebynn/quant/` | 存在 |
| `strategy_reversal.py` | `/home/pebynn/quant/` | 存在 |
| `strategy_chan.py` | `/home/pebynn/quant/` | 存在 |
| `daily_signals.py` | `/home/pebynn/quant/` | **空文件(0行)** |
| `send_signals_qq.py` | `/home/pebynn/quant/` | **不存在** |
| `daily_signal_report.py` | `/home/pebynn/quant/` | 存在 |

## 修复记录 (2026-05-13 01:28 执行)

### 执行步骤
1. **手动拉K线**: tushare `pro.daily(trade_date='20260512')` → 5490只, 0.4s拉取 + 7.7s批量UPSERT入MySQL
2. **跑策略信号**: `daily_signals.py` (275行, 三策略内嵌) → 14.9s完成，输出 `signals/signals_2026-05-13.json`
3. **投递QQ**: `send_signals_qq.py` → Queued `signals_2026-05-13_012919.json`

### 实际代码状态（纠正之前勘探）
| 文件 | 实际状态 | 行数 |
|------|---------|------|
| `daily_signals.py` | ✅ 存在（三策略内嵌实现） | 275行 |
| `send_signals_qq.py` | ✅ 存在 | - |
| `strategy_momentum.py` | ✅ 存在（非strategy_momentum_evo） | 22579行 |
| `strategy_reversal.py` | ✅ 存在 | 28432行 |
| `strategy_chan.py` | ✅ 存在 | 13289行 |

### 关键经验
- **K线管道根因**: tushare免费版 `pro.daily()` 偶发connection timeout（非代码bug）。cron无详细日志（no_agent模式），手动重跑即成功
- **stock-sdk MCP**: `get_a_share_quotes` 实时行情正常；`get_history_kline` / `get_kline_with_indicators` 连续fetch failed → 不依赖
- **数据源优先级**: 信号生成用MySQL kline表（本session已补全5/12数据）
