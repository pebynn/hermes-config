# Parquet三重读取I/O瓶颈诊断与修复 (2026-05-01)

## 问题

`daily_signal_report.py` 全市场扫描耗时 15.6 分钟，远超预期的 6-8 分钟。

## 根因：三重Parquet读取

数据流中存在三次独立的 parquet 读取链路：

```
第1遍: daily_signal_report.py L122-138 (串行)
  for code in codes_all:           # ~4966次
    kdf = pd.read_parquet(kp)      # 读取1: 检查市值
    cap = shares * kdf["收盘"][-1]
    if 50e8 <= cap <= 400e8: filtered.append(code)

第2遍: scan_signals() L728-755 (串行，在scan_signals被调用时)
  for code in codes:               # ~2500次
    kdf = pd.read_parquet(kp)      # 读取2: 再次检查市值
    cap = shares * kdf["收盘"][-1]
    if mc_min <= cap <= mc_max: filtered.append(code)

第3遍: _compute_one_stock() L616
  kline_df = pd.read_parquet(parquet_path)  # 读取3: 实际计算
```

**总计**: 每只股票 parquet 被读 3 次，全市场约 15000 次磁盘 I/O。

## 修复：单次读取 + 内联过滤

将市值检查合并进 `_compute_one_stock`，一次读取完成所有判断：

```python
def _compute_one_stock(code, kline_dir, industry, share_db, start_date,
                       mc_min=0, mc_max=float('inf')):
    kline_df = pd.read_parquet(parquet_path)  # 唯一一次读取

    # 市值检查（原 scan_signals 独立循环的逻辑）
    if (mc_min > 0 or mc_max < float("inf")) and share_db:
        shares = share_db.get(code)
        if shares is None:
            return None
        price = float(kline_df["收盘"].iloc[-1])
        cap = shares * price
        if not (mc_min <= cap <= mc_max):
            return None

    # 信号计算 ...（原有逻辑不变）
```

### 同步修改

- `scan_signals()`: 删除 L728-755 的独立市值过滤循环，改为注释说明逻辑已内联
- `daily_signal_report.py`: 删除 L121-148 的串行预过滤，直接 `parallel_scan(codes_all, MC_MIN, MC_MAX, n_workers=8)`
- `_scan_worker`: 签名改为 `(codes_chunk, mc_min, mc_max)`，透传给 `scan_signals`

### 配合优化

- N_WORKERS: 4 → 8（更多并行度）
- L2 质量门禁（`l2_score < 75 → return None`）进一步减少无效处理

## 效果

| 指标 | 优化前 | 优化后 |
|:-----|:------|:------|
| parquet 读取次数/股 | 3 | 1 |
| 全市场 I/O 次数 | ~15000 | ~4966 |
| N_WORKERS | 4 | 8 |
| 扫描耗时 | 15.6 min | 预估 6-8 min |

## 通用模式

任何需要「过滤 + 计算」的管线，如果过滤阶段需要读取完整数据后再在计算阶段重新读取，就应该将过滤逻辑合并进计算函数，在一次 I/O 中完成所有判断。这不仅适用于 parquet，也适用于任何「先扫一遍过滤、再扫一遍处理」的 CSV/数据库查询场景。

**反模式识别信号**:
1. 两个分离的循环读同一个文件集
2. 过滤循环丢弃了读取的数据（只保留了 key）
3. 计算循环又重新读同一批文件

**修复原则**: 数据只读一次，在同一个函数内完成所有需要该数据的判断。
