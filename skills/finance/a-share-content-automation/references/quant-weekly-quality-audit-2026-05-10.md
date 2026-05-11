# 量化周报质量审计 (2026-05-10)

## 发现的问题

### 1. 核心模块空占位
当 signal_engine / chan_buy 不可用时（周日/非交易日），原格式显示两个大段"⚠️ 暂不可用"，直接暴露给读者。

**修复**: 有数据才显示章节，无数据时跳过。`build_quant_report()` 改为 `has_signals / has_chan` 条件判断。

### 2. 数据无单位
`fmt_billion(207)` 返回 `"207"` 而非 `"207亿"`。数据已为亿单位，但函数按原始字节数判断。

**修复**: `fmt_billion()` 改为直接 `f"{abs(val):.0f}亿"`。

### 3. AI废话填充
原格式第七节"综合研判"和"关注方向"含大量模板话术：
- "多空信号均衡，市场缺乏明确方向。此时行业轮动和个股选择能力权重上升"
- "关注其驱动逻辑和龙头股走势以判断延续性"

**修复**: 删除大段话术，用基于数据的短句判断替代。

### 4. 板块全部"1次"
5个板块每个只上榜1次，全部列出毫无区分度。

**修复**: 过滤阈值≥2，只列出现2天以上的板块。加"主线/轮动中"判断。

### 5. 风险提示被截断
`scrub_ai_vocabulary` 的正则 `(建议|谨慎|可能|或许|大概率)` 将"投资需谨慎"中的"谨慎"误删。

**修复**: `shared_utils.py` L37 正则改为 `(?<!投资需)(建议|谨慎)(?!$)`。

### 6. 标题无SEO
原标题: `# A股量化周报 (2026-05-06 — 2026-05-08)`

**修复**: `量化周报 | 上证涨1.2% | XX领涨 | 主力加仓50亿`

### 7. 封面图缺失导致 40007
`push_to_wechat_draft()` 未传 `thumb_media_id` → WeChat API 返回 `[40007] invalid media_id`。

**修复**: `publish_draft.py` 新增 `_create_cover_pil()` PIL降级方案，matplotlib不可用时自动回退。

### 8. notify_qq NameError
`_write_success_log()` 内部调用了 `notify_qq(title, ...)` 但 `title` 不在该作用域。

**修复**: 移除死代码，`title` 从 `md_content.split("\n")[0]` 提取。

## 数据聚合问题（需单独修复）

`aggregate_weekly_data()` 的 `indices` 输出 `end=0.0` 导致指数表格空白。根因是 `all_data.json` 使用 `index` 字段但聚合逻辑可能读取 `close`。

`up_downs` 和 `turnovers` 字段在聚合后为空列表，需检查 `scan_available_data` 的数据加载路径。
