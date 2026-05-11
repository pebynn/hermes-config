# 早报多源降级实现 (2026-05-07)

## 背景

盘前早报（08:00）处于东方财富 push2 API 黑窗末期（19:00-08:00 不可用），AKShare 数据源不稳定。A50期货长期报 `Expected object or value` 错误。

## 解决方案

重构 morning_brief.py 数据采集层，使用多源降级链：

```
fetch_with_fallback(primary, fallbacks, name) → (data, source)
```

降级顺序：AKShare → Sina → 雪球，所有源失败才报错。

## 数据点降级链

| 数据点 | 降级链 | 当前主源 |
|--------|--------|---------|
| 美股三大指数 (DJI/NASDAQ/SP500) | AKShare → Sina (hq.sinajs.cn) | AKShare |
| A50期货 | AKShare → Sina → 雪球 | **Sina**（AKShare 08:00不可靠） |
| 恒生指数 | AKShare → Sina → 雪球 | AKShare |

## 新增函数

- `fetch_with_fallback(primary_fn, fallback_fns, name)` — 通用降级框架
- `_fetch_sina_us_indices()` — Sina 美股 (gb_dji/gb_ixic/gb_inx)
- `_fetch_sina_a50()` — Sina A50期货 (hf_CHA50CFD)
- `_fetch_sina_hsi()` — Sina 恒生 (int_hangseng)
- `_get_xq_source()` — 雪球懒加载 (from ~/quant/xueqiu_kline.py)
- `_fetch_xueqiu_a50()` — 雪球 A50期货
- `_fetch_xueqiu_hsi()` — 雪球恒生

## 输出标注

每个数据点标注实际数据源：
- `[AKShare]` — 主源成功
- `[Sina]` — 降级到Sina
- `[Xueqiu]` — 降级到雪球

## 附带修复

`format_change()` 双负号 bug：`跌-0.26%` → `跌0.26%`

## 验证

```bash
cd ~/.hermes/profiles/writing-domain/skills/a-share-data-collector/scripts
python3 morning_brief.py --no-push
```

预期输出：
```
📡 采集A50期货...
  ⚠️ A50期货 AKShare 失败: Expected object or value
  ✅ A50期货: 15770.16 (-0.26%) ▼ [Sina]
```
