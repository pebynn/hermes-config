# SZSE 两融接口列名修复 (2026-05-01)

## 问题

`ak.stock_margin_detail_szse(date='20260430')` 返回空 DataFrame，其他日期返回数据但列名与代码映射不匹配。

## 实际返回 vs 代码期望

| 实际列名 | 代码映射期望 | 状态 |
|:-----|:-----|:--|
| 证券代码 | 证券代码 → code | ✓ |
| 证券简称 | (无) | 新增，需排除 |
| 融资买入额 | 融资买入额 → margin_buy | ✓ |
| 融资余额 | 融资余额 → margin_balance | ✓ |
| 融券卖出量 | 融券卖出量 → short_sell | ✓ |
| 融券余量 | 融券余量 → short_volume | ✓ |
| 融券余额 | 融券余额 → short_balance | ✓ |
| 融资融券余额 | 融资融券余额 → total_balance | ✓ |
| (无) | 日期 → date | **缺失，需注入** |
| (无) | 融资偿还额 → margin_repay | **缺失，补NaN** |
| (无) | 融券偿还量 → short_repay | **缺失，补NaN** |

## 修复 (margin_data.py)

1. `SZSE_COL_MAP` — 移除不存在列（日期/融资偿还额/融券偿还量）
2. 新增 `SZSE_MISSING_COLS = ["margin_repay", "short_repay"]`
3. fetch_margin_daily 深市处理：
   - 排除证券简称列
   - `szse_df["date"] = _normalize_date(date_str_fmt)` — 注入日期
   - 补NaN到缺失列
4. `preload_margin_index` 日期归一化 YYYYMMDD → YYYY-MM-DD
5. `fetch_and_cache_date` 存盘名统一用归一化格式

## 残留限制

深市API不提供 `融资偿还额` / `融券偿还量` 字段 → L4 `l4_net_buy` 对深市股票恒为0。这是API天花板，非代码缺陷。
