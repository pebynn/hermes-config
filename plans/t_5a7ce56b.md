# Plan: R1-B 代码优化 — 扩展事件源提升信号密度
task_id: t_5a7ce56b
backtest_period: 2026-01-06 ~ 2026-04-30
target: 年化150%+ / 胜率>45% / LEVERAGE=1.0

## 数据现状
| 数据源 | 覆盖 | 状态 |
|--------|------|------|
| Sina K线 parquet | 100股, 2025-01~2026-04-30 | ✅ 可用 |
| Financial parquet | date/roe/yoy_revenue/debt_ratio/eps, ~5000股, 至2026-03-31 | ✅ 可用 |
| Fund Flow parquet | 2026-05-08~05-13 仅5天 | ❌ 无法用于回测 |
| MySQL K线 | 全量A股 | ❌ 无凭据 |

## 核心约束
- MySQL kline 不可用 → 必须改用 data_loader.py (Sina parquet)
- Sina kline 仅 100 股 → 选股池受限
- Sina kline 截止 2026-04-30 → 回测周期调整为 2026-01-06~2026-04-30
- Fund flow 数据仅5月 → 资金流确认无法使用, 改用量比/成交额增量代理

## 设计方案

### 方案选择: 改造现有 strategy.py → 使用 Sina parquet + Financial parquet

**选择理由**: MySQL 不可用, data_loader.py 已有成熟的 parquet 加载逻辑

**替代方案**: 直接用原 strategy.py + MySQL (已排除, 无凭据)

### 改进点映射 (5项→实际实现)

| # | 需求 | 数据约束 | 实现方案 |
|---|------|---------|---------|
| 1 | 扩展事件类型 | 仅financial有roe/yoy_revenue | 添加yoy_revenue>0过滤, roe>0过滤; SUE从1.5→1.0 |
| 2 | 降低事件门槛 | SUE≥1.0 即可 | SUE_THRESHOLD=1.0 |
| 3 | 资金流加速 | 无日内fund flow | 公告日量比>1.5 + 成交额>20日均值2x → 当日买入 |
| 4 | 缩短持有期 | 纯参数 | HOLD_MIN=5, HOLD_MAX=10 |
| 5 | 动量叠加 | K线可用 | pre_5d_ret ∈ (0, 0.20) |

### 新增过滤条件
- `yoy_revenue > 0`: 营收正增长 (财务数据)
- `roe > 0`: 盈利公司 (财务数据)
- `pre_5d_ret > 0 AND < 0.20`: 公告前5日动量合理
- `vol_ratio >= 1.5`: 保留量比过滤 (作为资金流代理)

### 参数变更
| 参数 | 旧值 | 新值 |
|------|------|------|
| SUE_THRESHOLD | 1.5 | 1.0 |
| HOLD_MIN | 15 | 5 |
| HOLD_MAX | 20 | 10 |
| MAX_PRE_RUNUP | 0.20 | 0.20 (不变) |
| STOP_LOSS | -0.12 | -0.10 (适度放宽) |
| MIN_POST_VOLUME_RATIO | 1.5 | 1.3 (放宽量比) |
| MIN_MARKET_CAP | 30e8 | 20e8 (放宽市值) |

### 风险
- 100股选股池极小 → 可能信号仍然不足
- SUE阈值下降可能引入噪音 → 胜率下降
- 持有期缩短 → 交易频率增加, 滑点影响加大
- 无MySQL数据 → 无法对比原结果

## 实施步骤
1. 改造 strategy.py: MySQL→parquet 数据加载 (使用 data_loader 模块)
2. 添加营收/ROE过滤 (yoy_revenue>0, roe>0 从 financial 数据)
3. 添加5日动量过滤 (pre_5d_ret ∈ (0, 0.20) 从 kline 计算)
4. 修改持有期/止损参数 (5-10天持有, -10%止损)
5. 调整回测周期到2026 (2026-01-06 ~ 2026-04-30)
6. TDD测试 (更新 test_strategy_b.py 适配新参数)
7. 运行回测验证 (输出 metrics 和 trades)

## 代码架构变更
### 原架构 (v3 procedural)
```
strategy.py (单体)
├── MySQL kline (sqlalchemy)
├── Financial parquet (直接读取)
├── 内联 SUE 计算
├── 内联事件检测
└── 内联回测引擎
```

### 新架构 (v4 modular)
```
strategy.py (改编)
├── data_loader.py → Sina kline + Financial + Share DB
├── factor_lib.py → SUE计算 + 动量计算 + 事件过滤
├── risk_manager.py → 仓位管理 + 退出逻辑
└── strategy.py → 主回测引擎 (调用上述模块)
```

## 数据流
```
Sina parquet kline (100股, 2025-01~2026-04-30)
  → load_kline_data() → DataFrame
  → 按 code 分组 → 逐股处理

Financial parquet (~5000股, 至2026-03-31)
  → load_financial_data(codes) → dict[code→DataFrame]
  → compute_pseudo_sue() + yoy_revenue/roe 过滤

事件检测 (逐股):
  find_event_v4(kline_df, fin_row) → event dict
    过滤链: SUE≥1.0 → yoy_revenue>0 → roe>0
           → pre_5d_ret∈(0,0.20) → vol_ratio≥1.3 → mcap≥20e8

回测引擎 (逐日):
  run_backtest(events, stock_klines) → (trades, nav)
    买入: 事件触发日, 等权分配, ≤10持仓
    退出: 持有5-10天 / -10%止损 / 5%止盈
```

## 测试策略 (TDD)
### RED 阶段新增测试
1. test_sue_threshold_lowered: SUE_THRESHOLD == 1.0
2. test_yoy_revenue_filter: yoy_revenue > 0 过滤生效
3. test_roe_filter: roe > 0 过滤生效
4. test_pre_5d_momentum: pre_5d_ret ∈ (0, 0.20)
5. test_hold_period_shortened: HOLD_MIN==5, HOLD_MAX==10
6. test_stop_loss_relaxed: STOP_LOSS == -0.10
7. test_backtest_period_2026: BACKTEST_START == '2026-01-06'

### 现有测试需更新
- test_17_strategy_has_config: 期望值变更 (SUE=1.0, HOLD_MIN=5, HOLD_MAX=10)
- test_14_exit_hold_period: 持有期参数变更

## 文件变更清单
| 文件 | 操作 | 说明 |
|------|------|------|
| strategy.py | 重写 | MySQL→parquet, 新过滤, 新参数 |
| test_strategy_b.py | 更新 | 新增测试, 更新期望值 |
| factor_lib.py | 扩展 | 添加 check_pre_5d_momentum() |
| data_loader.py | 不变 | 已有接口足够 |
| risk_manager.py | 不变 | 已有接口足够 |

## 验证步骤
1. pytest test_strategy_b.py -v → 全部 GREEN ✅ (21/21)
2. python strategy.py → 输出 metrics JSON ✅
3. 检查 metrics: total_trades > 0, annual_return_pct 计算正确 ✅
4. 检查 trades_detail.csv 和 nav_history.csv 生成 ✅
5. 手动检查几笔交易: buy/sell日期合理, pnl计算正确 ✅
6. kanban_complete with summary + metadata

## 回测结果 (v4)
| 指标 | v3 (2021-2025) | v4 (2026-01~04) |
|------|---------------|-----------------|
| 年化收益率 | 9.61% | -12.32% |
| 胜率 | 62.96% | 0.0% |
| 夏普比率 | 0.339 | -0.777 |
| 最大回撤 | -7.85% | -4.41% |
| 交易次数 | 135笔 | 7笔 |
| 事件数 | 418 | 8 |
| 选股池 | ~5000股(MySQL) | 100股(Sina) |

## 结果分析
### 未达目标原因
1. **选股池过小**: Sina parquet仅100股 vs MySQL原5000+股, 信号密度骤降
2. **时间窗口短**: 仅4个月, 事件全部集中在2026-02-24一天
3. **2026市场弱势**: 2-3月A股调整, 事件驱动策略无超额收益
4. **品质过滤过严**: yoy_revenue>0过滤掉51.5%候选; 整个100股池仅8事件

### 策略改进验证
- ✅ SUE 1.5→1.0: 候选从418扩至1738 (但都来自历史, 在窗口内的仅33)
- ✅ yoy_revenue>0 过滤: 生效, 过滤51.5%
- ✅ roe>0 过滤: 生效, 仅过滤3%
- ✅ pre_5d_momentum∈(0,0.20): 生效, 过滤15.2%
- ✅ HOLD_MIN/HOLD_MAX 5-10: 生效
- ✅ STOP_LOSS -10%: 生效
- ⚠️ 量比过滤已禁用 (公告日买入无需公告后量确认)

### 教训
- 100股选股池对事件驱动策略来说过小, 信号密度不足
- 短持有期(5-10天)在弱市中无缓冲余地
- 需要MySQL数据源或更宽的Sina数据覆盖才能实现目标年化150%+
- 报告日→公告日映射需考虑实际公告日期而非简单的+45天
