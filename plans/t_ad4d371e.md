# 策略A-主力资金动量增强 — 实施计划

> Task: t_ad4d371e | 创建日期: 2026-05-13 | 域: code

---

## 一、设计方案

### 1. 架构总览

```
quant/
├── shared/                          # 新建共享模块
│   ├── __init__.py                  # 空
│   ├── data_loader.py              # 数据加载 + 股票池过滤
│   ├── factor_lib.py               # 因子计算库
│   ├── risk_manager.py             # 风险管理
│   └── backtest_engine.py          # 回测引擎基类
├── strategies/
│   └── strategy_a_momentum/
│       ├── strategy.py              # 策略入口 (继承backtest_engine)
│       └── test_strategy.py         # TDD测试
├── data_common.py                   # 已存在: MySQL连接 + 工具函数
├── stock_fund_flow.py               # 已存在: 资金流数据模块
└── cache/
    └── sina_kline_2025_2026.parquet # 已存在: 100只股票K线
```

### 2. 数据流

```
data_loader.py
  ├── load_kline(source, start, end)     → DataFrame[code, date, OHLCV]
  │   ├── MySQL: kline表 (全A股)
  │   └── Sina: parquet缓存 (100只精选)
  ├── filter_universe(df, stock_list)    → 过滤后股票池
  │   ├── 市场: 主板 + 创业板
  │   ├── 排除ST (name含ST)
  │   ├── 排除新股 (list_date < 60天前)
  │   └── 日均成交额 >= 5000万 (近20日)
  └── load_fund_flow(date)              → DataFrame[code, main_net, ...]
      ├── 优先: ~/.finquant/cache/fund_flow/ parquet
      └── 回退: 量价代理因子 (volume_surge × direction)

factor_lib.py
  ├── compute_factors(kline_df)         → 因子DataFrame
  ├── fund_flow_factor(panel, ff_data)  → 5日主力净流入/流通市值 排名
  ├── momentum_factor(panel)            → 10日涨跌幅 排名
  ├── liquidity_factor(panel)           → 20日均换手率 排名
  └── composite_score(...)              → 加权综合排名

risk_manager.py
  ├── check_individual_stop(pos)        → 个股-8%止损
  ├── check_portfolio_stop(nav)         → 组合-15%止损 (从峰值)
  ├── is_month_restricted(date)         → 1月/4月空仓
  └── compute_position_size(capital)    → 等权分配

backtest_engine.py (基类)
  ├── class BacktestEngine
  ├── run()                             → 主循环
  ├── _compute_daily_nav()              → 使用prev_close逐日盯市
  ├── _record_trade()                   → 交易记录
  └── _report()                         → 统计输出

strategy.py (策略)
  ├── class FundFlowMomentumStrategy(BacktestEngine)
  ├── rebalance_weekly()                → 周一调仓
  ├── select_top_n(n=10)                → TOP10等权
  └── main()                            → CLI入口
```

### 3. 方案选择

| 决策点 | 选择 | 替代方案 | 风险 |
|:-------|:-----|:---------|:-----|
| **资金流数据** | 缓存优先 + 量价代理回退 | 仅用动量因子(退化为纯动量策略) | 代理因子可能不准确，降低资金流因子区分度 |
| **回测区间** | 2025-05-01 → 2026-04-30 (follow现有) | 仅用有资金流数据的日期(5月8-13日) | 代理因子回测的信噪比待验证 |
| **股票池** | 全部A股主板+创业板(MySQL) | Sina parquet 100只精选池 | MySQL性能压力，全量计算耗时长 |
| **调仓频率** | 每周一开盘 | 每日调仓(更高换手) | 周频可能错过短期动量，但符合任务要求 |
| **资金流代理** | vol_ratio × ret_sign × amount_ratio | Big-order ratio (大单净流入代理) | 代理精度有限，本质是量价模式 |
| **NAV计算** | prev_close逐日盯市 (per memory lesson) | entry_price基础计算 | 已确认entry_price方式导致NAV爆炸 |
| **市值计算** | close × shares (from share_db) | 仅用固定市值范围 | share_db需可用 |

### 4. 资金流代理因子设计 (关键!)

由于历史资金流缓存仅覆盖2026-05-08~13(6天)，回测期(2025-05~2026-04)绝大部分日期无真实数据。

代理公式:
```
proxy_fund_flow_score = vol_surge_score × direction_score

vol_surge_score:
  vol_ratio = volume_5d / volume_20d_avg
  score = min(vol_ratio, 2.0) / 2.0 × 100  # 0-100, 量越大越好

direction_score:
  ret_5d_signed = close_t / close_{t-5} - 1
  score = 50 + ret_5d_signed × 200  # 限制在0-100
  # 上涨=正向资金流，下跌=负向

final = 0.6 × vol_surge_score + 0.4 × direction_score
```

当真实fund_flow数据可用时，使用:
```
real_score = main_net / market_cap × 10000 (标准化)
```

### 5. 因子权重与打分

任务规格:
- 资金流因子 50%: 5日主力净流入/流通市值排名
- 动量因子 30%: 10日价格涨跌幅排名
- 流动性因子 20%: 20日平均换手率排名

实现方式: 等权排名打分 (非z-score)
```python
# 对每个因子，横截面排名 → 0-1分数
rank_score = factor_rank / total_stocks  # 0到1

# 加权合成
composite = (0.50 * fund_flow_rank_score +
             0.30 * momentum_rank_score +
             0.20 * liquidity_rank_score)
```

### 6. 风险参数

| 参数 | 值 | 说明 |
|:-----|:--|:-----|
| LEVERAGE | 1.0 | 无杠杆 |
| INDIVIDUAL_STOP | -0.08 | 个股止损-8% |
| PORTFOLIO_STOP | -0.15 | 组合从峰值回撤-15%触发平仓 |
| MONTHS_EMPTY | [1, 4] | 1月/4月空仓 |
| TOP_N | 10 | 持仓数 |
| REBALANCE_DAY | 0 (Monday) | 每周一调仓 |
| TC_COST | 0.001 | 单边0.1%手续费 |
| MIN_TURNOVER | 5e7 | 日均成交额>=5000万 |
| MIN_DAYS | 80 | 最少数据天数 |
| WARMUP_DAYS | 120 | 预热期 |
| MIN_MCAP | 5e9 | 市值>=50亿 |
| MAX_MCAP | 4e10 | 市值<=400亿 |

---

## 二、文件结构

### shared/__init__.py
空文件，标记为Python包。

### shared/data_loader.py
```python
class DataLoader:
    def load_kline(source='mysql', start, end) → DataFrame
    def load_stock_list() → DataFrame
    def load_share_db() → dict
    def load_fund_flow(date) → DataFrame | None
    def filter_universe(kline_df, stock_list, share_db) → list[str]
    def compute_market_cap(close, shares) → float
```

### shared/factor_lib.py
```python
class FactorLib:
    def compute_all_factors(kline_df) → DataFrame
    def fund_flow_factor(panel, date, ff_data) → Series
    def momentum_factor(panel) → Series
    def liquidity_factor(panel) → Series
    def composite_rank(factors_dict, weights) → Series
```

### shared/risk_manager.py
```python
class RiskManager:
    def __init__(config)
    def check_stop_loss(positions, current_prices) → list[(code, reason)]
    def check_portfolio_stop(current_nav, peak_nav) → bool
    def is_empty_month(date) → bool
    def can_enter(stock_data) → bool
```

### shared/backtest_engine.py
```python
class BacktestEngine:
    def __init__(config)
    def run() → (nav_series, trades_df)
    def _compute_nav(pos_prev, prices_today) → float
    def _execute_exits(signals) → list[Trade]
    def _execute_entries(signals) → dict[Position]
    def report() → dict  # annual, Sharpe, MDD, WR, etc.
```

---

## 三、测试策略 (TDD Step 3)

### 测试用例
1. `test_filter_universe` — 验证股票池过滤 (排除ST/新股/小市值)
2. `test_momentum_factor` — 验证10日涨跌幅计算
3. `test_liquidity_factor` — 验证换手率计算
4. `test_fund_flow_proxy` — 验证资金流代理因子边界
5. `test_composite_score` — 验证加权排名正确性
6. `test_stop_loss_trigger` — 验证-8%止损触发
7. `test_portfolio_stop` — 验证组合-15%回撤触发
8. `test_month_restriction` — 验证1月/4月空仓
9. `test_nav_calculation` — 验证prev_close NAV计算
10. `test_weekly_rebalance` — 验证周一调仓逻辑

---

## 四、实施步骤

### Phase 1: 基础设施 (shared/)
1. 创建 shared/ 目录和 __init__.py
2. 实现 data_loader.py — 数据加载+过滤
3. 实现 factor_lib.py — 因子计算
4. 实现 risk_manager.py — 风险管理
5. 实现 backtest_engine.py — 回测基类

### Phase 2: 策略实现
6. 实现 strategy.py — 继承基类，实现FundFlowMomentumStrategy
7. CLI入口 (--source mysql/sina)

### Phase 3: 测试与验证
8. 编写测试用例
9. 运行测试 → RED/GREEN循环
10. 运行完整回测
11. 验证输出结果合理性

---

## 五、风险与缓解

| 风险 | 严重性 | 缓解措施 |
|:-----|:------|:---------|
| 资金流代理因子无效 | HIGH | 设计时保留纯动量回退模式，代理因子权重可调 |
| MySQL全量加载慢 | MEDIUM | 分批加载，按code逐只计算因子(与现有strategy_momentum.py一致) |
| share_db缓存不可用 | MEDIUM | 回退到固定市值过滤(50-400亿用close×流通股本估算) |
| 周频调仓收益低 | LOW | 保持3日调仓作为可选参数，周一是任务硬性要求 |
| NAV计算复现lookahead | HIGH | 严格使用prev_close模式(已从Strategy B教训中验证) |

---

## 六、关键编码约定

1. **中文列名**: 遵循现有约定 — '日期','开盘','收盘','最高','最低','成交量','成交额'
2. **NAV公式**: `day_ret = (sum(cur_c/prev_close) - n_pos) / TOP_N * LEVERAGE`; `nav *= (1+day_ret)`
3. **因子计算**: 逐code计算，避免大panel操作 → 内存友好
4. **不修改回测区间**: 从base config继承，不在strategy.py覆盖
5. **T+1制度**: 使用昨日因子排名 → 今日开盘入场 (per现有模式)
