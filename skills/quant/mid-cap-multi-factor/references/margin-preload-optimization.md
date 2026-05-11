# margin-preload-optimization — 两融数据内存预加载优化 (v2.0, 2026-05-01)

## 问题

信号引擎 `_compute_layer4()` 为每只股票调用4次 margin_data 函数：
- `get_nearest_margin_date()` → 逐parquet扫描找股票
- `get_margin_trend()` → `load_margin_history()` → 打开~20个parquet
- `get_net_buy_intensity()` → `load_margin_cache()` + K线parquet
- `get_short_pressure()` → `load_margin_history()` → 又~20个parquet
- `load_margin_history()` (accel) → 又~20个parquet

全市场2000只股票 × 每只~60次parquet read = **~12万次磁盘IO**，大部分是重复打开同一文件。

## 方案

参考 K线更新从"5000次逐只API调用"→"tushare 1次批量调用"的优化思路：
**逐文件读盘 → 一次性内存预加载**

### 新增函数 (margin_data.py)

```python
preload_margin_index(n_days=10) → {code: {date_str: row_dict, ...}, ...}
```
- 扫 `~/.finquant/cache/margin/` 最近 N 个 parquet
- 一次性读入内存，构建股票代码→多日数据的字典索引
- 实测：5文件 × 2000只 = 9981条记录，<1秒完成

```python
query_margin_from_index(index, code, date_str, max_lookback=5) → row_dict | None
```
- O(1) 查询，替代 `get_nearest_margin_date() + load_margin_cache()`
- 精确匹配 → 向前回看max_lookback天

```python
query_margin_history_from_index(index, code, window=10) → [row_dict, ...]
```
- O(1) 查询，替代 `load_margin_history()`
- 按日期降序取最近window条，再反转升序

### 信号引擎改造 (signal_engine.py)

1. `_compute_layer4(code, ..., margin_index=None)` — 新增参数，优先走内存快速路径
2. `_compute_one_stock(..., margin_index=None)` — 透传参数
3. `scan_signals()` — 启动时调 `preload_margin_index(10)` 一次性加载

```python
# scan_signals() 中
if _L4_AVAILABLE and margin_data is not None:
    margin_index = margin_data.preload_margin_index(n_days=10)

# _compute_one_stock 中
l4 = _compute_layer4(code, kline_df, latest_kline_date, margin_index)
```

### 快速路径 vs 回退路径

```
margin_index is not None?
  ├── YES → 快速路径 (内存O(1)查询)
  └── NO  → 回退路径 (原始逐文件读取，保持兼容)
```

## 效果

| 指标 | 优化前 | 优化后 |
|:-----|:------:|:------:|
| parquet读取次数 | ~12万次 | 5次（预加载） |
| L4查询延迟/股 | ~60次文件IO | 纯内存O(1) |
| 预加载开销 | — | <1秒 |

L4 不再是信号扫描瓶颈。当前瓶颈在 L2 缠论检测（60只约15秒）。

## 推广模式

此优化模式适用于任何"逐文件读取 × N只股票"的场景：
1. 识别可批量预加载的数据源（按日期分片的parquet）
2. 在扫描入口一次性加载到内存索引
3. 下游查询从文件IO→dict/hash lookup
4. 保留原始逐文件路径作为回退

可应用到：财务数据、行业分类、股本数据库等。
