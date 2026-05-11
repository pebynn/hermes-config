# AI写作清洗实效审计 — 2026-05-06

## 现状

`generate_review.py` 的AI反写措施：

| 层 | 实现 | 覆盖范围 |
|:--|:-----|:--------|
| Prompt system | 中文禁用词列表(20+) + 禁用三连排比 + 禁用套话 | 弱约束，LLM遵从度不足 |
| 代码后处理 `scrub_ai_vocabulary()` | 23个Tier1中文词精确替换 | narrow |
| 违禁词拦截 | "建议"系列替换+兜底删除 | narrow |

## avoid-ai-writing 技能要求 vs 实际

| 技能要求 | 已实现 | 未实现 |
|:---------|:------|:------|
| Tier 1 词表(English 60+) | ❌ (只有中文版23词) | English版100+词全未覆盖 |
| Tier 2 聚类检测(同一段2+词告警) | ❌ | 无聚类逻辑 |
| Tier 3 密度检测(全文3%+占比告警) | ❌ | 无密度计算 |
| 结构层：段落均匀性检测 | ❌ | 无 |
| 结构层：句式节奏检测 | ❌ | 无 |
| 结构层：Em Dash密度 | ❌ | 无 |
| 结构层：标题大小写 | ❌ | 无 |
| 上下文profile匹配 | ❌ | 无 |
| Second-pass审计 | ❌ | 无 |
| content-creator `seo_optimizer.py` | ❌ | 未集成 |

## 今天泄露的AI痕迹（2026-05-06文章实测）

以下模式全部通过了当前23词scrub：

```
"飙升至"              → inflated language
"领涨全场"            → promotional
"交投活跃度提升"       → formulaic
"从历史经验看"         → vague attribution (无具体来源)
"是积极信号"           → significance inflation
"投资者可关注后续数据更新" → chatbot artifact
"可能反映出"           → hedging
"不仅...更..."         → compulsive pattern
"数据暂缺，无法..."     → cutoff disclaimer pattern
"若...则..."           → formulaic conditional
```

## 建议升级路径

### 短期（低工作量，高收益）
1. 扩展 `scrub_ai_vocabulary()` 词表至50+词（加入上述泄露模式）
2. 增加 Em Dash 密度检测（当前文章无此问题，但需防御）
3. 增加 "从历史经验看""值得关注的是""是积极信号" 等套话检测

### 中期
4. 集成 `content-creator` 的 `seo_optimizer.py` 做标题SEO评分（≥70分才通过）
5. 增加 Tier 2 聚类检测逻辑

### 长期
6. 完整的 second-pass 审计（调另一个LLM重读文章打分）
7. 上下文 profile 匹配（A股复盘应使用 `blog` profile）
