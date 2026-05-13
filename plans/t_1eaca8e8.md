# B-R5 比例权重增强 — 实施计划

> **Task**: t_1eaca8e8
> **Date**: 2026-05-13
> **基于**: B-R4调研报告 b4_proportional_research.md

---

## 设计方案

### 方案选择

| 决策点 | 选择 | 替代方案 | 理由 |
|:--|:--|:--|:--|
| 权重模块定位 | 独立 `policy_signal.py` | 内嵌到 factor_lib.py | 解耦，可独立测试，可ENABLE_POLICY_WEIGHT=False完全关闭 |
| 策略集成点 | 环节A(评分×) + 环节B(仓位加权) | 仅环节A | 双插入最大利用政策信号；仓位层面加权更直接反映信号强度 |
| API失败策略 | 返回中性权重 1.0 | 抛异常阻断 | 政策因子是辅助增强，不应因数据源故障阻塞交易 |
| 缓存策略 | 模块级 dict + TTL(3600s) | lru_cache | TTL控制过期，适合AKShare API速率限制 |
| 概念映射 | 懒加载+缓存至模块全局 | 每次请求 | 前100概念逐股查询耗时大(100+次API调用) |
| 情绪指数 | `index_news_sentiment_scope` | 自建模型 | 免费可用，零额外成本 |

### 架构设计

```
strategy_b_event/
├── policy_signal.py    ← ★ 新增: 政策消息面信号生成
│   ├── compute_policy_weight(code, date, kline_dict) → float
│   ├── batch_compute_policy_signals(events) → dict
│   ├── get_macro_sentiment(date) → float
│   ├── get_sector_excess(code, date) → float
│   ├── get_news_heat_anomaly(code, date) → float
│   ├── _load_concept_map() → dict
│   └── _CACHE: dict + TTL
│
├── factor_lib.py       ← 修改: 新增 score_event_with_policy()
├── strategy.py         ← 修改: 3个插入点
│   ├── main(): [3.5/5] 批计算policy_weight
│   ├── run_backtest(): 评分阶段 × policy_weight
│   └── run_backtest(): 仓位分配按权重配比
│
└── test_strategy_b.py  ← 修改: 新增 TestR5PolicyWeight
```

### 权重计算流程

```
compute_policy_weight(code, date)
    │
    ├─ 1. 宏观情绪 (大盘)          weight *= 1.08 or 0.92
    │   └─ index_news_sentiment_scope
    │
    ├─ 2. 板块异动 (行业级)        weight *= 1.0 + 0.3*tanh(z*0.5)
    │   └─ stock_board_concept_spot_em
    │
    ├─ 3. 新闻热度 (个股级)        weight *= 1.1 or 0.95
    │   └─ stock_news_em
    │
    └─ 4. clamp → [0.5, 1.5]
```

### 策略集成插入点

```
run_backtest 中:
  ┌─ 事件评分: ev['_score'] = score_event(...) * policy_weight
  └─ 仓位分配: alloc_i = cash × (pw_i / Σpw)
```

### 风险与缓解

| 风险 | 影响 | 缓解 |
|:--|:--|:--|
| AKShare API不可用 | 全部返回1.0 | try/except → 中性权重 |
| 概念映射构造慢 | 首次调用>30s | 懒加载+缓存，回测前预热 |
| 政策因子过拟合 | 权重极端偏离 | clamp [0.5, 1.5]，配置可调 |
| PEAD信号极弱(-14%) | 乘数效果有限 | 预期±20%微调，不设高目标 |

---

## 实施步骤

### Phase 1: 新建 policy_signal.py (~180行)
- [x] 1.1 缓存层 `_cached_call` + `_CACHE` dict
- [x] 1.2 `get_macro_sentiment(date)` → index_news_sentiment_scope
- [x] 1.3 `get_sector_excess(code, date)` → 板块超额Z-score
- [x] 1.4 `get_news_heat_anomaly(code, date)` → 新闻量异常度
- [x] 1.5 `_load_concept_map()` → 概念→成分股映射
- [x] 1.6 `get_stock_industry(code)` → 个股→行业反向查
- [x] 1.7 `compute_policy_weight(code, date)` → 核心权重函数
- [x] 1.8 `batch_compute_policy_signals(events)` → 批量计算

### Phase 2: 修改 factor_lib.py (~20行)
- [x] 2.1 新增 `score_event_with_policy()` 封装函数

### Phase 3: 修改 strategy.py (~30行改动)
- [x] 3.1 新增配置常量: ENABLE_POLICY_WEIGHT, POLICY_WEIGHT_RANGE 等
- [x] 3.2 新增导入: policy_signal, score_event_with_policy
- [x] 3.3 main() 中 [3.5/5] 批量计算政策权重
- [x] 3.4 run_backtest() 评分阶段 × policy_weight
- [x] 3.5 run_backtest() 仓位分配按权重配比
- [x] 3.6 结果输出中记录 policy 参数

### Phase 4: 测试 (TDD)
- [x] 4.1 test_r5_01: policy_signal 模块可导入
- [x] 4.2 test_r5_02: 默认权重=1.0 (无API时)
- [x] 4.3 test_r5_03: score_event_with_policy 一致性
- [x] 4.4 test_r5_04: 权重范围 [0.5, 1.5]
- [x] 4.5 test_r5_05: 策略导入policy_signal
- [x] 4.6 test_r5_06: ENABLE_POLICY_WEIGHT flag

### Phase 5: 回测验证
- [x] 5.1 运行完整回测 (2026-01-06 ~ 2026-05-13)
- [x] 5.2 ENABLE_POLICY_WEIGHT=True vs False 对比
- [x] 5.3 分析政策权重分布

---

## 配置参数

```python
# ── R5 政策消息面参数 ──
ENABLE_POLICY_WEIGHT = True          # 主开关
POLICY_WEIGHT_RANGE = (0.5, 1.5)     # 权重乘数范围
MACRO_SENTIMENT_ENABLED = True       # 宏观情绪
SECTOR_EXCESS_ENABLED = True         # 板块超额
NEWS_HEAT_ENABLED = True            # 新闻热度
DECAY_HALF_LIFE_DAYS = 7            # 衰减半衰期
```

## 验收标准

```
R5a (Phase 3.4): 仅环节A (评分层)
  预期: 交易数不变, 排序变化, 胜率微调
  验收: signal density unchanged

R5b (Phase 3.5): 环节A + 环节B (评分+仓位)
  预期: 仓位向政策友好股票倾斜
  验收: 回测可运行，无异常退出

预期效果: 年化收益±5%变化 (政策因子是辅助增强)
```
