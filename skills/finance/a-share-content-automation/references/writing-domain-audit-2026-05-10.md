# writing-domain 双管线架构与 2026-05-10 审计

## 管线拓扑

```
15:10 SEO管线: data_collector_seo.py → all_data_fresh.json → generate_review_seo.py → 草稿箱
15:15 小绿书:   generate_short_posts.py → 草稿箱
15:25 健康检查: pipeline_health_check.py
15:30 老管线:   collect_data.py + generate_charts.py → all_data.json + 图表
16:00 老管线:   generate_review.py → 读 all_data.json → publish_draft.py
```

双管线并行运行，数据格式有差异：
- `all_data_fresh.json` 额外含 `_cross_validation`, `_meta`, `data_completeness`
- `all_data.json` 来自老管线 collect_data.py

## 2026-05-10 审计发现与修复

### P0: data_guard.py 代码分叉

两个副本存在不同实现：
- `~/writing-data/shared/data_guard.py` (604行) — 完整版，含 `enforce_pipeline_gate`
- `~/writing-data/scripts/shared/data_guard.py` (145行) — 旧版，缺失 `enforce_pipeline_gate`

旧版被 `collect_data.py` 和 `generate_charts.py` 的相对导入使用。
修复：统一为完整版，清除 pyc 缓存。

### P0: generate_review.py 无交易日门禁

老版复盘脚本会尝试在非交易日生成复盘。已添加 `is_trading_day()` 检查。

### P1: generate_review_seo.py 冗余采集

`load_data()` 通过 subprocess 重新调用 `data_collector_seo.py`，
但 cron 已在 15:10 运行过采集器。修复：改为读缓存 `all_data_fresh.json`。

### P1: pipeline_health_check.py 缺失 SEO 脚本检查

## 审计检查清单（域脚本审计通用方法）

当审计一个域的脚本时，按以下顺序检查：

1. **导入链完整性**：`grep "from.*import" scripts/*.py | sort | uniq -c` — 找出所有跨文件导入，逐一验证函数存在
2. **代码分叉检测**：`find . -name "*.py" | xargs md5sum | sort | uniq -d` — 检测同名文件的多个副本
3. **静默失败模式**：搜索 `try: ... except.*ImportError:.*pass` 和 `except.*:.*print.*跳过` 模式
4. **cron 对齐**：对比 cron job 中调用的脚本名与实际文件名
5. **交易日门禁**：确认所有数据采集/生成脚本都有 `is_trading_day()` 检查
6. **冗余采集**：检查生成脚本是否重复调用采集器（cron 已覆盖的情况）
