# writing-domain 审计记录 (2026-05-06)

一次5维度全面审计，发现并修复4个问题。

## 发现清单

### 1. 冲突cron — e96600991bbb「每日A股市场复盘」21:05
- **问题**: Legacy任务用web_search搜A股表现，与writing-domain的AKShare数据管线完全重叠
- **影响**: 双轨产出复盘内容，web_search版质量低
- **修复**: 暂停cron任务 (paused 2026-05-06)

### 2. config.yaml死配置段 (120行→8行)
- **问题**: 以下段不被任何脚本实际读取，纯死配置:
  - `ai_apis` / `content_generation` / `formatting` / `data_collection`
  - `analysis` / `tracking` / `publishing` / `debug`
- **根因**: 脚本走 `~/.hermes/.env` 拿API密钥，不读config.yaml
- **修复**: 精简为model + delegation两段，模型字段统一为 `model.default`

### 3. SOUL.md与skill大面积重复 (333行→50行)
- **问题**: SOUL.md和a-share-content-automation skill描述同样的数据源架构、文章模板、工作流协议、cron配置
- **影响**: 修改一处需两处同步，维护负担重
- **修复**: SOUL.md瘦身为域身份+委托规则+红线(50行)，操作知识全归skill

### 4. 模型字段写法不一致
- **问题**: config.yaml用 `model.model:`，其他域用 `model.default:`
- **修复**: 统一为 `model.default: deepseek-v4-pro`

## 验证通过项

### 5个脚本语法检查 (全部OK)
- collect_data.py ✅
- generate_charts.py ✅
- generate_review.py ✅
- publish_draft.py ✅
- weekly_summary.py ✅

### 3个新cron任务 (last_run: null 正常)
- 5896e6bcea04 (15:30数据+图表) — 首个交易日2026-05-06
- d075c207d860 (16:00复盘+发布) — 同上
- 3858ff88add6 (周五16:00周总结) — 本周五首次运行
