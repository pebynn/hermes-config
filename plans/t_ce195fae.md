# Plan: 缠论策略优化 (R24-v5 → R25)

**Task**: t_ce195fae — T1: 缠论策略代码优化
**File**: /home/pebynn/quant/strategy_chan_opt.py
**Target**: 年化300%, 胜率45-55%, LEVERAGE=1.0
**回测**: 2025-05-01 → 2026-04-30

---

## 1. 现状诊断 (R24-v5 Baseline)

### 当前参数
| 参数 | 值 | 评注 |
|:--|:--|:--|
| MAX_HOLDINGS | 5 | 集中持仓 |
| MIN_HOLDINGS | 4 | |
| REBALANCE_INTERVAL | 5天 | 高频调仓 |
| STOP_LOSS | -8% | |
| TAKE_PROFIT | +8% | 偏低，限制收益空间 |
| MAX_HOLD_DAYS | 25天 | R23用30天效果更好 |
| VOL_RATIO_MIN | 2.0 | |
| BUY2_ACTIVE_DAYS | 12天 | |

### Sina基线 (100只，仅供参考)
- 年化: 18.48% (Sina仅100只，不可靠)
- 胜率: 55.6% ✅
- 45笔交易 (信号稀疏)
- 30/45笔 max_hold退出 (66.7%) → TP打不到
- 止盈13笔均+10.14%，止损2笔均-10.27%

### 关键瓶颈分析
1. **TP 8%太低**：R20用13%达到279%，R23用10%达到211%
2. **MAX_HOLD 25天太短**：30/45笔被max_hold砍掉（均值-0.71%），说明25天内不够完成趋势
3. **无trailing stop**：Strategy B reversal验证trailing_stop是冠军退出规则（均+2,558/笔）
4. **排名维度单一**：仅按量比排序，未考虑近期动量或趋势强度
5. **文档不一致**：docstring说-6%/15天，实际-8%/25天

---

## 2. 方案设计 — R25 (多维度增强)

### 方案选择: 复合增强路线

**核心思路**: 保留R24-v5的信号核心(3条入场)，强化退出机制+增加候选排序维度。

### 具体改动

#### A. 退出机制重构（最高优先级）
```
STOP_LOSS      = -0.08   (保持，硬止损底线)
TAKE_PROFIT    = 0.12    (8%→12%，匹配30天窗口)
MAX_HOLD_DAYS  = 30      (25→30天，给趋势更多呼吸空间)
TRAILING_ACTIVATE = 0.05  (新增：浮盈5%激活trailing)
TRAILING_DISTANCE = 0.03 (新增：从高点回撤3%触发退出)
```

**Trailing stop逻辑**:
- 持仓期间跟踪 highest_close
- 当 (highest_close - entry_price) / entry_price >= TRAILING_ACTIVATE 时激活
- 当 (close - highest_close) / highest_close <= -TRAILING_DISTANCE 时触发退出

#### B. 入场条件微调
```
BUY2_ACTIVE_DAYS = 10  (12→10天，更新鲜的信号)
新增条件: 收盘 > MA20 (短期动量确认，非核心过滤)
```

**理由**: 12天窗口太宽，10天保证信号新鲜度。MA20过滤确保短期也有动量支撑（非强制的软过滤：如果候选池<MIN，则放宽MA20要求fallback）。

#### C. 持仓与权重
```
MIN_HOLDINGS = 5  (4→5)
MAX_HOLDINGS = 7  (5→7，扩大候选池利用率)
权重: 等权 1/N (保持)
调仓: 5天 (保持)
```

#### D. 候选排名增强
```
旧: sort by vol_ratio descending
新: composite_score = vol_ratio * momentum_factor
    momentum_factor = max(1.0, (close - close_5d_ago) / close_5d_ago * 100 + 1.0)
    即: 5日动量≥0 → 1.0基准; 负动量打折; 正动量加成
```

#### E. 文档修复
修正docstring与实际配置一致。

### 替代方案（已评估，未采用）

| 方案 | 为什么不用 |
|:--|:--|
| R20参数直接复制 (12/10/13/0.13) | 279%年化但DD-34.77%，胜率47.9%偏低 |
| 加杠杆到1.5x | 任务明确要求LEVERAGE=1.0 |
| 添加time_stop（短期持仓退出） | R10验证time_stop是拖累（-226K） |
| 增加RSI过滤 | R23验证去除RSI改善，不加回 |

### 风险
- **trailing_stop参数过紧**: 3%回撤可能在正常波动中误触发，导致过早退出。需监控exit_reason分布。
- **候选池不足**: MA20过滤可能进一步减少候选，需要fallback机制。
- **MySQL数据量**: 全量4939只计算可能超时，需考虑性能。

---

## 3. 实施步骤

1. ✅ Brainstorming — 本文件
2. ✅ Writing plans — 本文件
3. ⬜ TDD — 编写测试用例 (trailing stop逻辑 + composite ranking)
4. ⬜ 编码 — patch strategy_chan_opt.py
5. ⬜ Debugging — 运行回测，检查结果
6. ⬜ Code review — 自审
7. ⬜ Verification — 年化≥300% 或 显著改善

---

## 4. 成功标准

| 指标 | 当前 | 目标 |
|:--|:--|:--|
| 年化 | ~18% (Sina) | ≥150% (优先突破) → 300% |
| 胜率 | 55.6% | 45-55% |
| 夏普 | 1.52 | ≥1.5 |
| 最大回撤 | -8.58% | ≤-35% |
| 交易笔数 | 45 | ≥150 |

---

## 5. 回传Lessons（待完成后填写）

[LESSONS]
- level: 🟢
  domain: code
  content: <pending>
  context: <pending>
