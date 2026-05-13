# 发布管线 v5.0 (2026-05-13) — 审核+图表+CDN+推送一体化

## 架构变更

旧管线：cron直接输出文章 → QQ Bot投递。无审核门禁，无配图，无微信草稿箱推送。

新管线：`publish_pipeline.py` 统一后处理所有6条内容cron。

```
cron生成文章 → 保存drafts/YYYY-MM-DD-{type}.md
                    ↓
publish_pipeline.py --file ... --title ... --domain ... --push
    ├── 1. review_article()      → AI词检测 + 字数检查 + 风险提示
    ├── 2. generate_charts()     → matplotlib K线结构图(200DPI/120KB)
    ├── 3. 上传微信CDN           → /cgi-bin/media/uploadimg → 替换本地路径
    ├── 4. HTML转换              → Markdown → 微信HTML格式
    ├── 5. 封面图                → wechat_cover.py(PIL生成900x500)
    └── 6. 推草稿箱              → /cgi-bin/draft/add(API access_token)
                    ↓
            review.verdict=APPROVED → QQ Bot投递
            review.verdict=BLOCK    → 修正后重试
```

## 关键决策

1. **登录态问题根除**：改用API access_token路径，不再依赖浏览器cookie。每次调用实时获取token，不存在"过期""失活"问题。

2. **审核门禁代码强制（非文本提醒）**：
   - BAN_WORDS 45+词（财经AI高频套话）
   - AI_SENTENCE_PATTERNS 6条正则
   - 字数下限(500字) + 风险提示检查
   - verdict: APPROVED | WARN | BLOCK

3. **配图生成**：
   - 左侧：K线结构图（阴阳线实体+上下影线，红绿对比）
   - 右侧：移动平均线示意（模拟走势+MA5/MA20）
   - DPI 200（手机端750px可读），暗色背景 #0d1117

4. **图片上传微信CDN**：`/cgi-bin/media/uploadimg` → 获取mmbiz.qpic.cn URL → 替换本地路径 → HTML中img src为CDN URL

## 已更新的cron（2026-05-13）

| cron_id | 名称 | domain |
|---------|------|--------|
| cb4e13762bf2 | 隔夜速递(05:35) | daily |
| e10e5bab3a4e | 午间热榜(11:35) | daily |
| f54a3f9f759a | 今日重磅(17:40) | event |
| 79e67133f2d0 | 全天回顾(23:35) | daily |
| 3858ff88add6 | 本周投资故事(周五17:00) | weekly |
| 11502faaf718 | 科普(每日18:00) | kepu |

## 脚本路径

- 管线脚本：`~/.hermes/scripts/publish_pipeline.py`
- 封面图：`~/.hermes/scripts/wechat_cover.py`
- matplotlib用：`/home/pebynn/tools/quant_env/bin/python3`

## cron prompt通用模板

所有6个cron的prompt遵循统一结构：
```
Step 1: 搜索+写作
Step 2: 保存到 ~/writing-data/drafts/YYYY-MM-DD-{type}.md
Step 3: python3 ~/.hermes/scripts/publish_pipeline.py --file ... --push
Step 4: read_file读取文章 → 完整内容作为最终回复（不附加状态汇报）
```

## 已知限制

- 封面图由PIL生成，非matplotlib（独立子系统）
- 审核仅覆盖AI词+字数+风险提示，不覆盖政治敏感/谣言检测（需更高级NLP）
- 微信草稿箱推送依赖WECHAT_APP_SECRET在~/.hermes/.env中配置
