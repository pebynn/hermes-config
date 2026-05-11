# Lens Adaptation for Business/E-Commerce Research

How to adapt the 9 generic research lenses to business/e-commerce platform topics like "拼多多全站式电商运营体系."

## Core Principle

The 9 lenses were written for general tech/scientific research. For business topics, reinterpret each lens through the company/platform's operational dimensions.

## Lens-by-Lens Adaptation

### 1. Technical → Platform Algorithms & Infrastructure
- Don't look for "physics/engineering specs"
- DO research: recommendation system, search ranking logic, traffic distribution mechanism, promotion tools (OCPX, full-site promotion), AI/ML usage
- Key queries: "[平台名] 推荐算法 流量分发 搜索排名"
- Sources: academic papers on platform mechanisms, industry reports, platform documentation

### 2. Economic → Revenue Model & Unit Economics
- Don't look for "macro economic indicators"
- DO research: revenue breakdown (advertising vs commission), take rates, GMV, merchant profit margins, cost structures
- Key queries: "[平台名] 财报 GMV 营收 商家利润"
- Sources: earnings reports (Tier 1), analyst reports (Tier 2), merchant interviews (Tier 3-4)

### 3. Historical → Company Evolution & Pattern Detection
- Don't look for "historical analogies across industries"
- DO research: founding story, key pivots, funding rounds, competitive responses, inflection points
- Key queries: "[平台名] 发展历程 关键转折 历史"
- Sources: company history timelines, 虎嗅/36氪 deep-dives, Wikipedia

### 4. Business → Competitive Landscape & Moat Analysis
- Don't look for "generic competitive frameworks"
- DO research: market share changes (2020-2024), competitor comparison matrix, moat sources
- Key queries: "[平台名] vs [竞品] 竞争格局 市场份额 2024"
- Sources: market share reports (雪球/高盛/QuestMobile), industry analysis

### 5. Strategic → Long-term Bets & Game Theory
- Don't look for "policy or regulatory frameworks" (unless relevant)
- DO research: expansion strategy (Temu/global), vertical bets (agriculture), transformation signals
- Key queries: "[平台名] 战略 全球化 Temu 未来布局"
- Sources: earnings call transcripts, CEO interviews, strategic initiative announcements

### 6. Customer → User Demographics & JTBD
- Don't look for "generic buyer personas"
- DO research: user age/income/geography data, time-spent metrics, purchase decision factors, pain points
- Key queries: "[平台名] 用户画像 消费行为 购买决策"
- Sources: QuestMobile reports (Tier 2), user surveys, platform consumer data

### 7. Product → Platform Features & Merchant Tools
- Don't look for "product specs or failure modes" (general)
- DO research: promotion tools, data analytics dashboard, activity/event system, seller operations flow
- Key queries: "[平台名] 推广工具 数据分析 活动体系 运营"
- Sources: platform documentation, merchant guides, 电商运营知识库

### 8. Contrarian → Stress-Test the Consensus
- Don't look for "abstract counter-arguments"
- DO research: merchant complaints, growth deceleration, regulatory risks, model sustainability
- Key queries: "[平台名] 商家困境 罚款 利润薄 增长放缓"
- Sources: investigative journalism (腾讯新闻/财新), merchant community reports

### 9. First-Principles → Rebuild from E-Commerce Fundamentals
- Don't look for "physics limits"
- DO research: what is the essential function of this marketplace? What are the irreducible transaction costs?
- Key queries: "[平台名] C2M 供应链 去中间化"
- Sources: founder philosophy (黄峥's writings), business model analysis

## Effective Search Patterns for Chinese E-Commerce Research

### Query Language
- Always search in Chinese for China-focused topics
- Combine: platform name + specific dimension + year
- Example: "拼多多 推荐算法 流量分发 2024"

### Productive Source Types
1. **Tier 1**: 财报 (earnings reports) — best for revenue/GMV/profit data
2. **Tier 2**: 券商研报 (broker research: 天风/东吴/中金) — best for industry analysis
3. **Tier 2**: QuestMobile reports — best for user behavior data
4. **Tier 3**: 电商运营知识库 (platform operations guides) — best for practical mechanisms
5. **Tier 3-4**: 虎嗅/36氪/晚点LatePost — best for strategic analysis
6. **Tier 4**: 腾讯新闻/新浪财经 — best for merchant narratives and controversies
7. **Tier 5**: 知乎/雪球 — best for sentiment and anecdotal evidence

### Batch Extraction
Use `web_extract` for deep content from multiple URLs at once:
- Limit to 3-5 URLs per call for best reliability
- Prioritize research reports and academic papers
- News articles often truncated; use as supplement only

## Pitfall: Disappearing GMV Data
- 拼多多 stopped disclosing GMV after 2022
- 淘宝天猫 stopped disclosing GMV after 2022年双十一
- Market share data from 2023+ is all third-party estimates (Tier 3)
- Always note the uncertainty when citing GMV figures

## Pitfall: index.md Lens Mismatch
The file `~/research-skill-graph/index.md` lists lens names (Empirical/Comparative/Systems/Stakeholder/Causal/Uncertainty/Ethical/Synthesis) that do NOT match the actual lens files. Always follow SKILL.md's lens listing and the actual lens files in `~/research-skill-graph/lenses/`. Index.md needs updating.
