# Chinese Financial Technical Analysis Research — Worked Example

## Context

This reference documents the Parallel Topic Burst pattern applied to a cross-language (Chinese + English) financial research task: deep research on A-share stock market technical analysis theories (缠论/Chan Theory, volume-price relationships, classic indicators, cross-theory integration).

## The Pattern in Action

### Step 1: Decompose into 4 orthogonal sub-topics

```
Topic: A股技术分析理论体系
├── Sub-topic 1: 缠论 (Chan Theory) — fundamentals, algorithms, quantification
├── Sub-topic 2: 量价关系 (Volume-Price Analysis) — 8 patterns,实战
├── Sub-topic 3: 经典技术指标 (MA/MACD/KDJ/BOLL) — quantitative backtest results
└── Sub-topic 4: 跨理论整合 & 量化平台 (Integration & Platforms)
```

### Step 2: Fire 4+ web_search simultaneously (one call)

Each search used a Chinese+English keyword mix to maximize coverage:
- `缠论 核心概念 分型 笔 线段 中枢 背驰 三类买卖点 量化实现`
- `Chan theory 缠中说禅 李彪 技术分析 缠论量化 算法实现 python`
- `A股量价关系 量在价先 放量突破 缩量回调 天量天价 地量地价 实战分析`
- `A股技术指标 均线 MACD KDJ 布林带 实战有效性 量化选股`

### Step 3: Scan results for top URLs per sub-topic

Sources found per sub-topic (examples):
- 缠论: 中泰证券研究报告, BigQuant wiki, GitHub chan.py (1700 stars)
- 量价关系: 东方财富网财富号, 富途量价8种关系, 同花顺量价图解
- 经典指标: 东北证券2023报告(32指标回测), 华泰证券择时研究
- 整合: 五维共振系统详解, 聚宽/MACD+KDJ组合

### Step 4: Extract key pages in parallel

Extracted from:
- 雪球缠论精髓3分钟掌握
- BigQuant缠论wiki
- 东北证券32指标择时报告PDF
- 五维共振交易系统详解

### Step 5: Apply 9 lenses with the knowledge base

Each lens was applied with the specific findings already gathered, making the lens analysis richer than a sequential approach would have produced.

## Key Takeaways for Future Sessions

1. **Language mixing**: Chinese keywords find different content than English. Always search in both for any China-related financial topic.

2. **Academic PDFs are key**: Chinese broker research reports (券商研报) are Tier 2 sources with rare quantitative backtest data. They often appear as PDFs rather than HTML pages. Use targeted `web_search` queries that include "报告" or "PDF".

3. **GitHub repos are data source**: For 缠论量化, the GitHub repos (chan.py, chanlun-pro) provided implementation detail unavailable in prose articles. Always include GitHub searches for technical implementation topics.

4. **Blog platforms vary**: 知乎 (Zhihu) and 雪球 (Xueqiu) have different content quality — 雪球 is more finance-specific, 知乎 is more general but sometimes deeper. Check both.

5. **Index.md lens discrepancy**: The `research-skill-graph/index.md` lists a different lens set (Empirical/Historical/Comparative/Systems/Stakeholder/Causal/Uncertainty/Ethical/Synthesis) than the `SKILL.md` and `lenses/` directory (technical/economic/historical/business/strategic/customer/product/contrarian/first-principles). Follow the SKILL.md + lenses/ directory — those are the authoritative source. The index.md needs updating to match.

## Generated Knowledge Base

This research produced:
- `projects/stock-trading-theory-research/executive-summary.md` — 5 key findings
- `projects/stock-trading-theory-research/deep-dive.md` — 16KB full 9-lens analysis
- `projects/stock-trading-theory-research/key-players.md` — 18 entities (authors, brokerages, open-source projects, platforms)
- `projects/stock-trading-theory-research/open-questions.md` — 9 unresolved questions
- Wiki update: 20 concepts + 13 data points added to knowledge base
