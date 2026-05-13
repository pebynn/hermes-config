# 组合止损冷却机制：stop_once → ps_cooldown 修复

## 问题

策略A v2 的 `strategy_v2.py` 中组合止损（portfolio stop）使用 `stop_once` 布尔标志：

```python
pos = {}; trades = []; prev_nav = 1.0; peak = 1.0; stop_once = False

# 每日回测循环：
ps_hit = (ps > 0 and dd <= -ps and not stop_once)  # 仅首次触发
if ps_hit: stop_once = True  # 触发后永久置True
```

**后果**：组合止损触发一次后，`stop_once=True` 永久生效，后续任何深度的回撤都不再被拦截。全期回测（含多段下跌）中回撤可跑到-54.6%——首次-15%触发清仓后，剩余-39%无保护。

## 修复方案：ps_cooldown 冷却机制

```python
pos = {}; trades = []; prev_nav = 1.0; peak = 1.0; ps_cooldown = 0  # 冷却天数

# 每日回测循环：
if ps_cooldown > 0: ps_cooldown -= 1              # 冷却递减
ps_hit = (ps > 0 and dd <= -ps and ps_cooldown == 0)  # 冷却期满可触发

# 买入条件：冷却期内禁止买入
if rday and not ps_hit and ps_cooldown == 0 and xr is not None:

# 触发后：
if ps_hit: ps_cooldown = 20  # 20天冷却
```

**四处改动**（`strategy_v2.py`）：
1. `stop_once = False` → `ps_cooldown = 0`
2. 循环内加 `if ps_cooldown > 0: ps_cooldown -= 1`
3. `ps_hit = (dd <= -ps and ps_cooldown == 0)`
4. 买入条件加 `ps_cooldown == 0`
5. `if ps_hit: ps_cooldown = 20`

## 2025年回测对比验证

| 指标 | ps=10% | ps=15% |
|:-----|:------|:------|
| 年化收益 | 747.3% | -0.8% |
| 总收益 | 685.0% | -0.8% |
| 夏普比 | 6.74 | -0.02 |
| 最大回撤 | -10.6% | -18.5% |
| 胜率 | 44.9% | 41.6% |
| 交易笔数 | 390 | 77 |
| 组合止损触发 | 4次 | 2次 |

## 关键发现

1. **ps=10% 优于 ps=15%**：更紧的止损线→更早截断亏损→冷却后重新入场抓反弹→390笔交易→回撤锁定在-10.6%
2. **ps_cooldown 机制有效**：4次反复触发+冷却+重新入场，而非触发一次后躺平
3. **2026年数据无触发**：最大回撤仅-6.9%，10%和15%阈值均未触发，结果一致

## 运行注意

- `run_backtest_v2(ps=0.10, ...)` 默认参数在函数定义时绑定，必须显式传参
- 全年回测（243天+5000只股票）不可并行运行——OOM
- 串行运行~180s/次
