# szse-margin-data-issue — 深市两融数据问题 (已修复, 2026-05-01)

> 状态: 已修复 — 详见 references/szse-margin-column-fix.md

原问题: AKShare stock_margin_detail_szse() 返回空或 'date' 列 KeyError。
根因: SZSE API 列名已变更（无 日期/融资偿还额/融券偿还量，多 证券简称）。
修复: 更新 SZSE_COL_MAP + 注入 date 列 + 补 NaN 缺失列 + 日期格式归一化。

修复后深市 ~2080 只正常拉取，L4 覆盖从 5% -> 88%。
残留: l4_net_buy 对深市为 0（API 无偿还额）；20260430 劳动节延迟发布。
