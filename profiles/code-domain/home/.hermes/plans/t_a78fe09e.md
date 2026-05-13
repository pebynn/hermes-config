# R2-C-代码修复-核心问题修复 — 实施计划

> Task ID: t_a78fe09e
> 工作目录: /home/pebynn/quant/strategies/strategy_c_policy/
> 回测周期: 2026-01-06 ~ 2026-05-13
> 目标: 年化150%+ / 胜率>45% / LEVERAGE=1.0

---

## 1. 设计方案

### P0: MCP概念选股修复 — EastMoney fallback

**问题**: `_load_top_concepts()` 和 `_load_concept_constituents()` 依赖MCP stock-sdk binary (`~/.hermes/node/lib/node_modules/stock-sdk-mcp/dist/index.js`)，若binary不存在则返回空列表，导致概念选股完全失效。

**方案选择**: 使用EastMoney概念板块API直接获取概念列表和成分股

**替代方案**: 
- A) 使用akshare的概念板块接口 — 但akshare未在项目中安装
- B) 预缓存概念数据到parquet — 需要额外的数据管道
- C) 直接从EastMoney API实时获取 — 依赖外部API但可以缓存

**选择C**: 使用EastMoney公开API获取概念板块数据，首次获取后缓存到`~/.finquant/cache/concepts/`，后续回测从缓存读取。

EastMoney概念列表API:
```
http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&po=1&np=1&fltt=2&fid=f3&fs=m:90+t:3&fields=f2,f3,f4,f12,f14
```
- `m:90+t:3` = 概念板块
- 返回字段: f2(最新价), f3(涨跌幅), f4(涨跌额), f12(板块代码), f14(板块名称)

EastMoney概念成分股API:
```
http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&fltt=2&fid=f3&fs=b:BKxxxx&fields=f12,f14
```
- `b:BKxxxx` = 概念板块代码(如BK0815)
- 返回成分股列表

**风险**: EastMoney API可能限流；缓存策略缓解。ipv6路由问题(已知)，需force ipv4。

### P1: 调仓频率修复 — 月度调仓

**问题**: `is_rebalance_day()` (risk_manager.py)仅检查`dayofweek == rebalance_dow`，不支持月度调仓。StrategyC配置了`rebalance_weekly: False`但该参数未被使用。

**方案**: 在`RiskManager.is_rebalance_day()`中增加`rebalance_weekly`参数判断:
- `rebalance_weekly=True`: 按dayofweek周度调仓（现有逻辑）
- `rebalance_weekly=False`: 每月第一个交易日调仓

月度调仓检测逻辑:
```python
if not rebalance_weekly:
    # 检查是否为当月第一个有数据的交易日
    # 通过前后日期比较: 当前日期的月份 != 前一个日期的月份
    # 调用方需传入all_dates列表
```

**修改点**: 
1. `risk_manager.py`: `is_rebalance_day()`增加`rebalance_weekly`和`all_dates`参数
2. `backtest_engine.py`: 调用is_rebalance_day时传入config中的rebalance_weekly

**替代方案**: 在StrategyC子类中重写is_rebalance_day逻辑 — 但修改基类更优雅。

### P2: 仓位管理优化

**a) 分批建仓 (2-3只/批)**
在`backtest_engine.py`的入场逻辑中，限制每次调仓的净新增持仓数:
```python
max_new_per_day = min(3, top_n - len(existing_positions))
```

**b) 组合止损从-15%放宽至-20%**
修改StrategyC的配置: `portfolio_stop: -0.20`

**替代方案**: 不修改基类，在StrategyC._select_stocks中限制返回数量 — 但这只影响选股，不影响建仓节奏。

### P3: 代码清理 — 删除strategy_c_policy/shared/

**当前状态**: `strategy.py`已从`/home/pebynn/quant/shared/`导入（通过sys.path设置），`strategy_c_policy/shared/`是冗余副本。

**操作**: 直接删除`strategy_c_policy/shared/`目录及其所有文件。验证`python3 strategy.py --source sina`仍可运行。

### P4: JSON输出

在`main()`中增加:
```python
import json
report_path = os.path.join(output_dir, "backtest_results.json")
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2, default=str)
```

### P5: 市场择时 — 大盘趋势过滤

**问题**: R1在下跌市场中频繁入场导致亏损。

**方案**: 使用上证指数/创业板指作为大盘代理，计算MA20和MA60关系:
- MA20 < MA60: 熊市 → 仓位减半(top_n从10减到5)
- 其他: 正常仓位

**实现**: 在`data_loader.py`中增加`load_market_index()`方法，在`StrategyC._select_stocks()`中根据大盘趋势动态调整top_n。

**挑战**: 需要能获取指数K线数据。如果sina parquet包含指数数据则直接用，否则用简单代理（如全市场等权收益）。

---

## 2. 文件修改清单

| 文件 | 修改类型 | P级别 | 
|------|---------|-------|
| `strategy.py` | 修改 | P0, P2b, P4, P5 |
| `shared/risk_manager.py` | 修改 | P1 |
| `shared/backtest_engine.py` | 修改 | P1, P2a |
| `shared/data_loader.py` | 新增方法 | P0, P5 |
| `strategy_c_policy/shared/` | 删除 | P3 |
| `tests/test_strategy_c.py` | 新增测试 | 全部 |

---

## 3. 测试策略

1. **单元测试**: MCP fallback逻辑，is_rebalance_day月度模式，分批建仓逻辑
2. **集成测试**: `python3 strategy.py --source sina --start 2026-01-06 --end 2026-05-13` 完整回测
3. **验收标准**: 
   - 代码可运行无报错
   - 月度调仓生效 (~4-5批次 vs R1的14批次)
   - 年化收益改善（从-18.45%提升）
   - JSON输出文件生成

---

## 4. 实施顺序

P3 (代码清理) → P0 (概念选股) → P1 (调仓频率) → P2 (仓位管理) → P5 (市场择时) → P4 (JSON输出)

P3先做因为删除shared/后可验证导入无断裂。
P4最后做因为依赖report对象。

---

## 5. 回退方案

如修改后回测结果劣于R1基准(-18.45%)，逐个回退P5 → P2 → P0，保留P1(调仓频率)作为最低改进。
