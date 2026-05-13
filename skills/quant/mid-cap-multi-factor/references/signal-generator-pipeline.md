# 策略信号生成器管线架构

2026-05-14 从 strategy_a_v2 信号生成器构建过程中提炼。

## 核心思路

把回测循环拆成"每日收盘后跑一次 → 出信号 → 次日开盘执行"的管线。

```
回测: 一次循环遍历所有交易日, 模拟买卖
信号: 每天收盘跑一次, 基于最新数据生成次日信号
```

差异仅在于:
- 回测模拟资金曲线
- 信号版输出买卖列表 + 持仓状态

因子计算、排名逻辑、停损条件 **100%复用回测代码**。

## 管线架构

```
15:30  cron: K线更新 → MySQL
16:08  cron: signal_generator.py
         ├─ MySQL拉K线(120天预热)
         ├─ 计算因子面板 (复用 compute_factors_v2)
         ├─ 计算排名 (复用 compute_composite_score_v2)
         ├─ 读 positions.json (持仓/NAV/冷却状态)
         ├─ 判卖: 硬止损/移动止盈/排名掉落/组合止损
         ├─ 判买: 调仓日 + 动量过滤 + topN
         ├─ 写 signals/signals_YYYY-MM-DD.json
         └─ stdout摘要 → QQ Bot投递
```

## 状态持久化 (positions.json)

```json
{
  "positions": {
    "000004": {"ep": 12.50, "in": "2026-05-12", "high_close": 13.20, "pc": 13.00}
  },
  "peak_nav": 1.45,
  "current_nav": 1.23,
  "ps_cooldown": 5,
  "last_date": "2026-05-15"
}
```

### 关键设计: 买入价自修复

买入信号生成时, 次日开盘价未知 → `ep=0.0` 占位。下次运行时:
```python
if p.get("ep", 0) <= 0 and c in today_xt.index:
    p["ep"] = float(today_xt.loc[c, "开盘"])  # 用当日开盘价填充
    p["pc"] = float(today_xt.loc[c, "收盘"])
    p["high_close"] = max(p["ep"], p["pc"])
```
无需人工更新持仓文件。

## 信号输出格式

```json
{
  "date": "2026-05-18",
  "rebalance": true,
  "buy": [
    {"code": "000001", "reason": "rank", "score": 2.35, "ret_5d": 0.045}
  ],
  "sell": [
    {"code": "000002", "reason": "trail"},
    {"code": "000003", "reason": "stop"}
  ],
  "hold": ["000004", "000005"],
  "pending_entry": [],
  "top10": ["000001", "000002", ...],
  "portfolio": {"nav": 1.23, "peak": 1.45, "dd_pct": -15.1, "ps_cooldown": 5}
}
```

## 执行节奏

| 时间 | 动作 |
|:--|:--|
| 15:05 | K线数据就绪(MySQL) |
| 16:08 | cron触发 signal_generator.py |
| 16:09 | 输出 signals_YYYY-MM-DD.json |
| 16:09 | stdout摘要 → QQ Bot投递 |
| 次日9:25 | 人工按信号挂单 |

## QQ Bot投递模式

### no_agent cron + stdout直投

```
cron: no_agent=true, script=signal_a_v2.sh, deliver=qqbot:TOKEN
        ↓
signal_a_v2.sh → python signal_generator.py (stderr静默, stdout保留)
        ↓
stdout内容 → QQ Bot原样投递
```

### 踩坑: cron脚本路径限制
`no_agent` cron的 `script` 参数必须是 `~/.hermes/scripts/` 下的文件名, 不支持绝对路径。解决方案: 在该目录放一个wrapper shell脚本。

```bash
#!/bin/bash
# ~/.hermes/scripts/signal_a_v2.sh
cd /home/pebynn/quant/strategies/strategy_a_momentum
exec /home/pebynn/tools/quant_env/bin/python signal_generator.py 2>/dev/null
```

## 与现有cron的时序协调

| 时间 | cron | 用途 |
|:--|:--|:--|
| 15:30 | K线更新 (afff56398abe) | 每日K线写入MySQL |
| 15:35 | 复盘管线+资金流 (双cron) | 大盘+个股资金流 |
| 15:40 | 资金流预采集 (81c6af2f5573) | stock-sdk缓存 |
| 15:50 | L4两融数据拉取 (18edaa02cd7e) | 融资融券 |
| **16:08** | **策略A信号 (f7904d71ee1c)** | 本管线 |
| 16:10 | 三策略每日信号 (0637e225e375) | 旧版投递 |
| 21:00 | 信号日报 (b60f3c86dd1b) | 多因子选股 |
