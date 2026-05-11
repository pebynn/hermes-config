# Writing-Domain Lessons — A股内容自动化教训

## 🔴 CRITICAL

### 数据铁律：禁止自行计算或推断涨跌幅/涨跌家数
- ✅ **已升格** → `profiles/writing-domain/SOUL.md` 🔴硬约束段 (2026-05-07)
- **纠正次数**: 4
- **规则**: 涨跌幅、成交额、换手率、涨跌家数等所有数字必须来自 API 原始返回值
- **禁止**: 用 (close-prev_close)/prev_close 自己算涨跌幅
- **禁止**: 用涨停数×28、跌停数×15 推断涨跌家数 — 纯属捏造
- **原因**: 复权/除息/停牌等情况会导致自行计算完全错误；推断比例无统计依据
- **正确**: 直接取 API 返回的涨跌幅字段；涨跌家数用专用API (stock_zh_updown_statistics)
- **来源**: 2026-05-07 generate_review.py 第101行 int(lu*28) 捏造 2772/500/1728，真实数据 3513/1831/161

### Sina API parts 映射铁律
- ✅ **已升格** → `profiles/writing-domain/SOUL.md` 🔴硬约束段 (2026-05-07)
- parts[1]=今开, parts[2]=昨收, parts[3]=收盘, parts[4]=最高, parts[5]=最低, parts[9]=成交额
- 东财 push2: f43=最新价, f170=涨跌幅×100
- 之前映射错误致全盘数据错误 — 映射错误=全部错


### 管线门禁不可跳过: data_guard在5个入口点强制执行
- data_guard已集成点: collect_data(采集后验证) / generate_charts(图表生成后检查) / generate_review(草稿保存后审计) / weekly_summary(草稿保存后审计) / publish_draft(发布前审计)。所有门禁走audit_guard四维审计。不提供跳过选项——发现BLOCK必须修改后重新生成，不能绕过。
- **纠正次数**: 1
- **首次发现**: 2026-05-08

### data_guard 门禁是强制性的，不管风险等级都不能绕过
- data_guard 输出 BLOCK → 管线必须停止，不可强行发布。输出 WARN → 可以继续但必须记录警告。只有 PASS → 才允许正常发布。脚本内的 data_guard 集成代码不可删除/注释/绕过。每日06:00 drift 检测会检查同名函数实现差异，发现差异会报警。
- **纠正次数**: 1
- **首次发现**: 2026-05-08
## 🟠 HIGH

### 东方财富 API 晚间维护
- 北京时间 19:00-08:00 全部 _em 端点不可用 (RemoteDisconnected)
- 应对: Sina 备用数据源 (vip.stock.finance.sina.com.cn, 34行业板块)
- 图表缓存优先 + signal alarm 30s 超时
- cron 15:30 不受影响

### 双管线并存：老管线(all_data.json) + SEO管线(all_data_fresh.json)
- 老管线: 15:30 collect_data.py → 16:00 generate_review.py (读 all_data.json)
- SEO管线: 15:10 data_collector_seo.py → generate_review_seo.py (读 all_data_fresh.json)
- generate_review_seo.py 不再自行采集（去掉了 load_data 中的 subprocess 调用）
- 两套管线数据格式不完全相同，注意 all_data_fresh.json 额外有 _cross_validation/_meta/data_completeness 字段

### data_guard.py 双副本已统一 (2026-05-10)
- 旧版 scripts/shared/data_guard.py(145行) 缺失 enforce_pipeline_gate
- 完整版 shared/data_guard.py(604行) 含 enforce_pipeline_gate + 六部分完整功能
- 已统一为同一文件，pyc缓存已清除
- generate_review.py 老版已添加交易日门禁 (is_trading_day)

### avoid-ai-writing 后处理不可跳过
- 所有图文内容生成后必须经过 avoid-ai-writing 后处理
- 含 content-creator SEO 优化
- Tier1-3 三层清洗 + 第二遍审计 + '建议'兜底删除

### 双脚本一致性铁律
- 改 generate_review.py（每日复盘）必须同步检查 weekly_summary.py（周总结）
- 涉及: 数据源、图表引用、avoid-ai-writing词表、SEO、API降级


### 配图生成规范: 禁用PIL小字号手动绘图
- 科普/复盘配图文字模糊问题是PIL ImageFont小字号(13-20pt)+低分辨率导致。解决方案: ①安装matplotlib,用plt+中文配置(wqy-zenhei)生成高DPI图表 ②PIL绘图必须2x分辨率降采样,标题字号≥36pt,标注≥20pt ③K线图/均线图等结构图用matplotlib专业图表函数,不使用PIL手动draw ④布局验收标准: 文字在手机端(750px宽)阅读清晰、灰色标注可辨识、不依赖细线(1px)渲染。触发: generate_popular.py或任何配图生成场景强制遵循。
- **纠正次数**: 1
- **首次发现**: 2026-05-09
## 🟡 MEDIUM

### 雪球 vs 新浪交叉验证
- 晚间黑窗用雪球 fill_indices_from_xueqiu() 回填
- 3-way 交叉验证: AKShare ↔ Sina ↔ 雪球
- 写入 _cross_validation.xueqiu_vs_sina

### 公众号平台AI内容识别风险 — AI生成不给推荐流量
- 平台已能识别"AI一键生成"内容，不给予推荐流量，新号尤其明显
- **策略**: "AI搭框架、人工填灵魂" — AI用于效率（初稿/标题/图片），不能替代人工审核和人格化润色
- **禁止**: 纯AI生成不加人工处理的内容输出（触发降权/零推荐）
- **正解**: avoid-ai-writing后处理 (Tier1-3清洗) + audit_guard AI味检测 + 人工审核兜底
- **来源**: 20260509_023044_855a59（deep-research发现）

### Sina API 也可能不可用 — 需要第三备源
- Sina 是 东方财富 的默认备源，但 Sina 本身也会失效
- Sina API 不可用 → 板块/资金流/涨跌停全部为空 → 连锁故障
- 解决方案: 配置第三备源（雪球/同花顺）作为自动降级链路的最后一环
- 当前管线故障模式: Sina 不可用 → 核心数据缺失 → AI 写出劣质内容 → 发布失败
- **来源**: 20260506_104750_8ed504

### 发布管线自动退避重试
- 发布管线三级降级（API→Cookie→Browser）全部失败后，不要立即放弃
- 应实现: 首次失败 → 5min 后自动重跑 `publish_draft.py --date <date> --type <daily|weekly>`
- 尤其是 `errcode: 50002`（配额限频），限频解除后有恢复窗口
- **来源**: 20260506_104750_8ed504