# 北向资金雪球晚间降级链

**日期**: 2026-05-07 | **状态**: 已投产

## 问题

AKShare `stock_hsgt_fund_flow_summary_em()` 在晚间(19:00-08:00 CST)不可用，导致 `signal_engine.py` 的北向乘数永远为 1.0。晚间 cron (21:30 复盘) 的北向环境加成完全失效。

## 解决方案

三态回退链：**AKShare → 雪球指数快照推断 → 默认 multiplier=1.0**

### 降级逻辑 (signal_engine.py L1097-1119)

```
try:
    AKShare stock_hsgt_fund_flow_summary_em()  → nb_net = 实际值 亿元
except:
    try:
        雪球 kline_fallback.get_northbound_flow()  → nb_net = 推断值 亿元
        if nb_net == 0: _log("雪球推断无方向，multiplier=1.0")
    except:
        _log("全不可用，multiplier=1.0")
```

### 雪球推断算法 (xueqiu_kline.py::get_northbound_flow)

雪球没有直接的北向资金汇总 API。通过 4 大指数的快照涨跌幅间接推断：

```
get_indices_snapshot() → 4大指数 {SH000001, SZ399001, SZ399006, SH000688}
→ 提取 percent 字段
→ 判断逻辑:
   ├─ 全部 4 指数同向 > +0.3%  → inflow = avg_pct × 50 亿元
   ├─ 全部 4 指数同向 < -0.3%  → outflow = avg_pct × 50 亿元 (负数)
   ├─ 平均绝对值 < 0.15%       → 0.0 (横盘，无方向)
   └─ ≥75% 同向 且 avg > 0.3%  → avg_pct × 30 亿元 (混合信号，衰减)
      └─ 否则 → 0.0
```

### 校准依据

- 1% 平均指数涨幅 ≈ 50亿北向净流入 (经验校准，基于对北向资金单日最大值~200亿、指数单日最大涨幅约4%的观测)
- 混合信号衰减系数 30 (vs 50) — 指数方向不完全一致时信号可靠性打折

### 影响范围

- `signal_engine.py` L1107-1119: 北向资金获取异常处理
- `xueqiu_kline.py` L260-314: `XueqiuSource.get_northbound_flow()` 推断方法
- `kline_fallback.py` L96-111: `get_northbound_flow()` wrapper (import → delegate → 0 on fail)

### 依赖

- `~/.hermes/credentials/xueqiu_cookies.json` — 雪球 cookie (与 writing-domain 共享)
- Cookie 有效期 ~30 天，需手动刷新

### 测试

```python
cd ~/quant && python3 -c "
from kline_fallback import get_northbound_flow
print(f'北向推断: {get_northbound_flow()} 亿元')
"
# 工作日收盘后应返回非零值，凌晨/周末返回 0.0
```

## 限制

1. **推断，非真实数据** — 指数涨跌与北向流入非严格线性关系
2. **横盘失效** — 当指数波动 < 0.15% 时无法判断方向，返回 0
3. **板块分化失效** — 当 4 大指数方向不一致 (< 75% 同向) 时返回 0
4. 不建议用于实盘资金决策，仅作为 L2/L3/L4 共振乘数中的微弱加成 (×1.05)
