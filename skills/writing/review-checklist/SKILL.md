---
name: review-checklist
description: 公众号内容审核 — 数据准确性/排版规范/合规检测/标题优化。writer产出后、发布前的强制门禁。
version: 1.0.0
allowed-tools:
  - read_file
  - search_files
  - web_search
  - terminal
  - skill_view
execution: manual
when-to-use: |
  当reviewer需要审核writer产出的公众号文章时加载。
  检查维度：数据准确性、排版规范、合规风险、标题吸引力、AI味残留。
  适用于每日复盘、周总结、量化周报、科普内容等所有公众号文章类型。
related-skills:
  - avoid-ai-writing
  - humanizer
  - data-accuracy-layer
  - a-share-content-automation
---

# Review Checklist — 公众号内容审核门禁

## 审核流程

按以下顺序逐项检查，任一项FAIL即block。

### Step 1: 加载文章
```
read_file 目标文章路径
```

### Step 2: 数据准确性（P0）
- [ ] 所有数字（涨跌幅、成交额、指数点位）需要与源数据一致
- [ ] 日期、星期、交易日判断正确
- [ ] 指数名称和代码对应正确
- [ ] 涨跌家数、涨停/跌停数在合理范围
- **验证方式**: 对照 `~/writing-data/raw/<date>/all_data.json` 逐字段核对
- **常见错误**: 涨跌幅用错基准（open vs prev_close）、成交额单位混乱（万元/亿元）

### Step 3: 排版规范（P0）
- [ ] H2标题用橙色背景 `## <span style="background:#FF6600;color:#fff;padding:2px 8px;border-radius:3px">标题</span>`
- [ ] H3标题用橙色左边框 `### <span style="border-left:3px solid #FF6600;padding-left:8px">标题</span>`
- [ ] 正文字号15px
- [ ] 段落间距合理（不超过5行连续无空行）
- [ ] 图表引用路径正确，图片文件存在

### Step 4: 合规检测（P0）
- [ ] 无敏感政治表述
- [ ] 无投资建议/推荐具体股票（可描述不可推荐）
- [ ] 无虚假信息/谣言
- [ ] 风险提示完整（至少一处"投资有风险"或等效表述）
- [ ] 不涉及色情/暴力/违法内容

### Step 5: 标题审查（P1）
- [ ] 标题长度8-60字
- [ ] 不含AI相关字样（AI/AIGC等）
- [ ] 有吸引力但不标题党
- [ ] 与正文内容一致

### Step 6: AI味检测（P1）
- [ ] 加载 `avoid-ai-writing` skill进行AI味检测
- [ ] 检查是否有"综上所述""值得注意的是""由此可见"等AI标志词
- [ ] 段落首句是否多样化

### Step 7: 综合判定
- 全部通过 → APPROVED
- P0项不通过 → BLOCK（必须修正）
- 仅P1项不通过 → WARN（可发布但需下次改进）

## 输出格式

```
## 审核报告: <文章标题>

| 维度 | 结果 | 问题 |
|:--|:--|:--|
| 数据准确性 | ✅/❌ | ... |
| 排版规范 | ✅/❌ | ... |
| 合规检测 | ✅/❌ | ... |
| 标题审查 | ✅/⚠️ | ... |
| AI味检测 | ✅/⚠️ | ... |

综合判定: APPROVED / BLOCK / WARN

## 修改建议
1. ...
2. ...
```

## 常见拒绝模式

| 模式 | 判定 | 修正方式 |
|:--|:--|:--|
| 涨跌幅与源数据偏差>0.1% | BLOCK | 重新采集数据 |
| 缺少配图或配图路径错误 | BLOCK | 重新生成图表 |
| 缺少风险提示 | BLOCK | 添加风险声明 |
| AI标志词>3处 | WARN | 运行avoid-ai-writing |
| 标题<8字 | WARN | 优化标题 |
| 图表过小(<1KB) | BLOCK | 重新生成图表 |
