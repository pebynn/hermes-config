# 2026-05-01 信号引擎优化记录

## 变更摘要

| 变更 | 文件 | 效果 |
|:-----|:-----|:-----|
| L2 质量门禁 ≥75 | `signal_engine.py` L654-656 | 信号从~2495收窄至200-500 |
| 市值过滤内联到 `_compute_one_stock` | `signal_engine.py` L627-635 | 消除3次→1次 parquet 读取 |
| 删除 `scan_signals` 独立市值过滤循环 | `signal_engine.py` L744-745 | 原28行逐只读盘代码移除 |
| 删除 `daily_signal_report` 串行预过滤 | `daily_signal_report.py` 原L121-148 删除 | 不再逐只读4966个parquet做市值检查 |
| N_WORKERS 4→8 | `daily_signal_report.py` L36 | 并行度翻倍 |
| Cron 16:00→16:30 | cronjob `c9f9c3e17687` | 给 K 线更新管线留30分钟余量 |

## 数据流变更

```
旧: parquet读①(预过滤) → parquet读②(scan_signals市值) → parquet读③(_compute)
新: parquet读①(_compute: 市值检查 + L2检测 + L1因子 + L3指标 全在一次)
```

## _compute_one_stock 关键路径 (优化后)

```python
def _compute_one_stock(code, kline_dir, industry="", share_db=None,
                       start_date="2024-07-01", mc_min=0, mc_max=inf):

    kline_df = pd.read_parquet(parquet_path)      # 唯一一次读盘
    kline_df = kline_df[kline_df["日期"] >= _sd]   # 日期截断

    if len(kline_df) < 50: return None              # 数据不足

    # 市值过滤 (内联，消除第2次读盘)
    if mc_min>0 or mc_max<inf:
        cap = share_db[code] * kline_df["收盘"].iloc[-1]
        if not (mc_min <= cap <= mc_max): return None

    buy2 = detect_chan_buy2(kline_df)               # L2检测
    if buy2.empty: return None

    l1 = _compute_layer1(code, kline_df, ...)       # L1因子
    l3 = _score_l3_from_latest(kline_df)             # L3量价
    l2_score, l2_level = _score_buy2(buy2.iloc[-1])

    if l2_score < 75: return None                    # L2质量门禁

    return {...}
```

## L2 质量门禁说明

`_score_buy2()` 返回 50/75/100 三档：
- 100 (强): ATR适中 + vol_ratio<0.5 + pullback深度>1.0 ATR
- 75 (中): 满足基本条件
- 50 (弱): 边际条件

门禁设在 ≥75，仅"中"和"强"信号进入综合排名。
