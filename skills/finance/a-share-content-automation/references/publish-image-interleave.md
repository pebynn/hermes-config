# 发布图片交错插入规范

## 当前状态（v2.1 — 2026-05-06）

`publish_draft.py` 的 `interleave_images()` 负责将已上传微信CDN的图表插入HTML对应章节。

### 每日复盘映射（6图 → 4章节）

| 章节关键词 | 图表 | 说明 |
|:--|:--|:--|
| 大盘回顾 | kline.png | K线图 |
| 资金风向标 | capital_flow.png | 资金流向 |
| 资金风向标 | volume_compare.png | 成交量对比 |
| 热点 | sector_heatmap.png | 板块热力 |
| 热点 | sector_rotation.png | 板块轮动 |
| 技术看盘 | market_breadth.png | 涨跌分布 |

### 周总结映射（6图 → 3章节）

| 章节关键词 | 图表 | 说明 |
|:--|:--|:--|
| 本周行情回顾 | kline.png | K线图 |
| 本周行情回顾 | capital_flow.png | 资金流向 |
| 本周行情回顾 | volume_compare.png | 成交量对比 |
| 最热方向 | sector_heatmap.png | 板块热力 |
| 最热方向 | sector_rotation.png | 板块轮动 |
| 下周展望 | market_breadth.png | 涨跌分布 |

## 陷阱

1. 同章节多图必须用 `defaultdict(list)` 聚合一次性插入，逐张覆盖会丢图
2. 图片不存在 CDN URL 时不插入（静默跳过）
3. 新增图表后必须同时在 `section_images` 列表和 `weekly_summary.py` 的图表引用列表中各加一行
