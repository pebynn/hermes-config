# 每日复盘跨日对比模块 (Rolling Cross-Day Comparison)

2026-05-10 新增，`generate_review_seo.py`。

## 设计动机

旧版每日复盘只做单日快照。升级后每天对比前5交易日数据，输出3个跨日维度。

## 实现架构

`_compute_rolling_trends(date_str)` → `_load_previous_days(date_str, 5)` 扫描 RAW_DIR 历史 → 计算 trend/capital_3d/hot_sectors → 注入 prompt 跨日对比段落。

## 局限性

- data_collector_seo.py 不采集 sectors/capital_flow → 两项可能为空
- 周一首个交易日历史数据不足 → 跳过
