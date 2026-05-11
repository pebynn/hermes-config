---
name: content-creator
description: SEO优化内容创作 — 品牌语气分析、博客撰写、社交媒体内容适配、内容日历规划。含品牌声音分析器+SEO优化器+内容框架库
version: "1.0.0"
author: "Alireza Rezvani"
source: "Commonly-used-high-value-skills"
tags: ["content", "creator", "growth", "marketing", "seo"]
created_at: "2026-03-18"
updated_at: "2026-03-20"
---
# Content Creator

SEO 优化的内容创作工具集。覆盖品牌语气建立、博客撰写、社交媒体内容适配、内容日历规划。

## 核心工作流

### 1. 建立品牌语气（首次设置）
- 分析现有内容建立基线：`python scripts/brand_voice_analyzer.py content.txt`
- 选择语气属性（3-5 个）并记录到品牌指南
- 撰写 3 篇样本测试一致性

### 2. 创建 SEO 优化博客
- 关键词研究：主关键词 500-5000/月搜索量，3-5 个次关键词
- 内容结构：用内容框架模板，关键词在标题/首段/2-3个H2
- 优化检查：`python scripts/seo_optimizer.py blog.md "keyword"`
- 关键词密度 1-3%，正确标题层级，内链+外链

### 3. 社交媒体内容
- 选择平台，适配格式
- 优化：适当长度+最佳发布时间+正确图片尺寸+平台特定话题标签

### 4. 内容日历规划
- 40/25/25/10 内容支柱比例
- 批量创作保持语气一致

## 参考文件

- `references/brand_guidelines.md` — 品牌语气指南
- `references/content_frameworks.md` — 内容框架模板库
- `references/social_media_optimization.md` — 平台优化指南
- `assets/content_calendar_template.md` — 内容日历模板

## 边界

- 不生成图片/视频素材
- 不管理社交媒体发布
- SEO 建议需人工审核后执行