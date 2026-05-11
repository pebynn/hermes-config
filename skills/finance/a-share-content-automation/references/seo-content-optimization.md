# SEO内容优化管线 (2026-05-09)

## 新增脚本

### `data_collector_seo.py` — 轻量实时采集器
- **位置**: `~/writing-data/scripts/data_collector_seo.py`
- **用途**: SEO管线专用采集，不依赖现有collect_data.py的缓存
- **三源并行采集**（threading，最长等30s）:
  1. stock-sdk (腾讯 Node.js): 指数点位+涨跌幅+全A涨跌家数+涨停统计+主力资金
  2. Sina (hq.sinajs.cn HTTP): 指数点位+涨跌幅+成交额
  3. 东方财富AKShare (subprocess 15s超时): 指数确认（目前IP封锁，超时自动跳过）
- **交叉验证**: 点位偏差>1%或涨跌幅偏差>0.5%标记警告，选中位数源作为最终值
- **合理性校验**: 成交额5000-100000亿范围检查
- **输出**: `~/writing-data/raw/{date}/all_data_fresh.json`

### `generate_review_seo.py` — SEO优化复盘生成器
- **位置**: `~/writing-data/scripts/generate_review_seo.py`
- **来源**: 从 `generate_review.py`复制改造，原文件不变
- **核心改动**:
  - 标题公式: `情绪钩子+数字+关键词+日期` → `主力资金跑了319亿，A股今天却在涨？`
  - 搜一搜关键词: `_compute_seo_keywords()`自动从数据提取8个tags+元描述
  - SEO导语: 前100字含核心数据作为搜索摘要
  - 关注钩子: 文末互动引导+关注引导
  - 数据源: 优先实时采集，兜底缓存
  - `--no-push`参数可跳过自动推草稿箱
- **cron**: `8aa4c853cff3` — 交易日15:10，no_agent=true
- **输出**: `~/writing-data/drafts/{date}-每日复盘.md`

### `generate_short_posts.py` — 小绿书短内容
- **位置**: `~/writing-data/scripts/generate_short_posts.py`
- **用途**: 从数据提取3-5个亮点→短图文→不占群发配额
- **提取类型**: index(指数)/fund(资金)/limit(涨跌停)/sector(板块)/volume(量能)
- **去重机制**: 同类型只保留优先级最高的
- **cron**: `108ce7535e38` — 交易日15:15，no_agent=true
- **输出**: `~/writing-data/drafts/{date}-小绿书.md`

### `generate_popular.py` — 理财科普文章
- **位置**: `~/writing-data/scripts/generate_popular.py`
- **用途**: 独立于每日复盘的科普内容线，AI写作→PIL封面图→直接推公众号草稿箱
- **核心流程**: call_deepseek() → create_cover() → upload_image()+push_draft()
- **选题映射**: TOPIC_MAP将关键词映射为完整文章标题
- **⚠️ pitfall**: 科普文章≠复盘文章。不走publish_draft.py管线，独立推草稿箱API。封面图用PIL生成（因服务器无matplotlib），非复盘风格。
- **--no-push**参数跳过草稿箱推送

### `wechat_auto_reply.py` — 股票代码自动回复（已取消）
- 因公网IP动态变化+无固定域名，此功能已撤回
- CTA中不得出现"回复股票代码查资金"类未上线功能描述

## SEO关键指标

| 指标 | 策略 |
|:-----|:-----|
| 搜一搜关键词 | 每篇自动提取8个关键词注入标题+导语+小标题 |
| 标题打开率 | 情绪钩子+数字+痛点公式，替代客观陈述式标题 |
| 搜一搜摘要 | 前100字含核心数据+关键词 |
| 互动转化 | 文末CTA（互动问题+关注引导） |

## 关键词矩阵

详见 `references/seo-keyword-matrix.md`（50+财经长尾关键词，P0-P2分级）

## 常见pitfall

### ❌ CTA承诺了尚未上线的功能
在文末写"回复股票代码查资金"之前，必须先部署好自动回复服务并配置微信后台。否则用户收到的是"该公众号暂未开通此功能"。
**修复**: CTA只写已上线的功能。未上线的写"即将上线"或不写。

### ❌ 不同的内容类型走同一条推送管线
科普文章的封面风格、排版、发布时间都与每日复盘不同。不能通过`publish_draft.py --type daily`推送科普。
**修复**: 每类内容独立处理推送。复盘走publish_draft.py管线，科普走独立草稿API调用（generate_popular.py内建）。

### ❌ 生成内容不配图
科普文章只有文字没有封面图，推草稿箱时thumb_media_id为空，读者看到的是默认灰图。
**修复**: 任何公众号内容生成脚本必须包含：文章内容+封面图+草稿箱推送。三步缺一不可。
