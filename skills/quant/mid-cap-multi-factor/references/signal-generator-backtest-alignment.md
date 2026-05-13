# 信号生成器与回测逻辑对齐清单

## 问题背景

2026-05-14 发现 signal_generator.py 与 strategy_v2.py 存在三处逻辑不一致，导致信号生成器的买入排名与回测Top10不同。根因：修改回测代码后忘记同步更新信号生成器。

## 强制对齐检查点

每次改动 strategy_v2.py 后，必须逐项检查 signal_generator.py：

| # | 检查项 | 回测 (strategy_v2.py) | 信号生成器 (signal_generator.py) | 本次发现 |
|:--|:------|:----------------------|:----------------------------------|:---------|
| 1 | 股票池前缀过滤 | `not (c.startswith('688') or c.startswith('92'))` | `build_universe` 无过滤 | ✅ 已修复 |
| 2 | ST排除 | `excluded_stocks.json` 加载 | `build_universe` 无加载 | ✅ 已修复 |
| 3 | 买入动量字段 | `xr.loc[c].get('mom', np.nan)` → `ret_10d` | `rank_xr.loc[code].get('ret_5d', np.nan)` | ✅ 已修复为 `mom` |
| 4 | 买入执行时机 | `pending_buys` → 次日开盘 | `_pending_entry` → 下次运行自动填充 | ✅ 一致 |
| 5 | 排名函数 | `compute_composite_score_v2(xr, weights, MIN_AMOUNT_V2)` | `compute_composite_score_v2(rank_xr, weights, MIN_AMOUNT)` | ✅ 一致 |
| 6 | 组合止损 | `PORTFOLIO_STOP_V2=0.10` + `ps_cooldown` | `PORTFOLIO_STOP=0.10` + `ps_cooldown` | ✅ 一致 |
| 7 | 动量阈值 | `MOM_ENTRY_THRESHOLD=0.02` | `MOM_ENTRY_THRESHOLD=0.02` | ✅ 一致 |
| 8 | 市值过滤 | `midcap_codes.json` 加载 | `build_universe` 未加载 | ⚠️ 待同步 |

## 本次修复详情

### 修复1: build_universe 加688/92/ST过滤

```python
# 修复前: 只有天数+成交额过滤
def build_universe(df, min_days=MIN_DAYS, min_amount=MIN_AMOUNT):
    code_counts = df.groupby("code").size()
    valid_codes = code_counts[code_counts >= min_days].index
    # ... 直接做成交额过滤

# 修复后: 增加前缀+ST过滤
def build_universe(df, min_days=MIN_DAYS, min_amount=MIN_AMOUNT):
    code_counts = df.groupby("code").size()
    valid_codes = code_counts[code_counts >= min_days].index
    
    # Filter: exclude 688 (STAR), 92 (BSE)
    valid_codes = [c for c in valid_codes if not (c.startswith('688') or c.startswith('92'))]
    
    # Filter: exclude ST
    _excl_path = STRATEGY_DIR / "excluded_stocks.json"
    if _excl_path.exists():
        with open(_excl_path) as f:
            _exclude_st = set(json.load(f))
        valid_codes = [c for c in valid_codes if c not in _exclude_st]
    
    # 最近20日日均成交额过滤...
```

### 修复2: 买入动量从ret_5d改为ret_10d(mom)

```python
# 修复前 (signal_generator.py L370-376):
ret_5d = float(rank_xr.loc[code].get("ret_5d", np.nan))
if check_momentum_entry(ret_5d, MOM_ENTRY_THRESHOLD):
    buy_signals.append({..., "ret_5d": round(ret_5d, 4)})

# 修复后:
ret_10d = float(rank_xr.loc[code].get('mom', np.nan))
if check_momentum_entry(ret_10d, MOM_ENTRY_THRESHOLD):
    buy_signals.append({..., "ret_10d": round(ret_10d, 4)})
```

注意: `check_momentum_entry` 函数接受任何数值(不区分5d/10d)，所以传错参数不会报错，而是静默使用错误的过滤逻辑。

### 修复3: 摘要显示文本

`"5日动量{b.get('ret_5d', 0):.1%}"` → `"10日动量{b.get('ret_10d', 0):.1%}"`

## 预防机制

1. **修改回测后运行信号生成器验证**: `python signal_generator.py` → 对比Top10是否合理
2. **共享常量考虑提权**: `MIN_AMOUNT`、`MOM_ENTRY_THRESHOLD` 等两处定义的值，统一到 `strategy_v2.py` 导入
3. **过滤器统一函数**: 考虑将 `build_universe` 替换为从 strategy_v2 导入的共享函数
