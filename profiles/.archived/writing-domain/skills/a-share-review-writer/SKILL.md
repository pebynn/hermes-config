---
name: a-share-review-writer
description: A股每日复盘文章生成技能 - 基于采集数据生成结构化复盘文章
version: 1.0.0
author: Hermes
license: MIT
related_skills: [a-share-data-collector, a-share-publisher]
scripts: [generate_review.py, generate_charts.py, weekly_summary.py]
---

# A股每日复盘文章生成技能

基于采集的A股数据，使用AI生成符合微信公众号风格的结构化每日复盘文章。

---

## 触发条件

- a-share-data-collector完成数据采集后
- 用户主动请求："写今日复盘"
- 域主代理编排调度

---

## 执行流程

### Step 1: 读取原始数据
1. 从 ~/writing-data/raw/YYYY-MM-DD/ 读取JSON数据
2. 验证数据完整性：
   - [ ] 大盘指数完整（4个指数均存在）
   - [ ] 资金流向数据存在
   - [ ] 板块数据存在
   - [ ] 个股亮点数据存在

### Step 2: 计算关键指标
```python
# 涨跌家数比
up_down_ratio = up_count / down_count if down_count > 0 else float('inf')

# 涨停跌停比
limit_ratio = limit_up_count / limit_down_count if limit_down_count > 0 else float('inf')

# 成交额比例
volume_ratio = today_amount / avg_5day_amount  # 较5日均量

# 北向资金态度
if north_flow > 50: sentinel = "大幅流入"
elif north_flow > 10: sentinel = "小幅流入"
elif north_flow > -10: sentinel = "持平"
elif north_flow > -50: sentinel = "小幅流出"
else: sentinel = "大幅流出"
```

### Step 3: 生成复盘洞察
基于数据提取关键洞察点：
```python
insights = []

# 大盘判断
if all(index["change_pct"] > 0 for index in index_data.values()):
    insights.append("三大指数集体收涨，市场情绪偏暖")
elif all(index["change_pct"] < 0 for index in index_data.values()):
    insights.append("三大指数集体收跌，市场情绪偏弱")
else:
    insights.append("指数分化，结构性行情明显")

# 量能判断
if volume_ratio > 1.2:
    insights.append("成交量放大，市场交投活跃")
elif volume_ratio < 0.8:
    insights.append("成交量萎缩，市场观望情绪浓厚")

# 资金判断
if north_flow > 30 and main_force > 0:
    insights.append("北向+主力资金共振流入，做多信号")
elif north_flow < -30 and main_force < 0:
    insights.append("北向+主力资金共振流出，防御为主")
```

### Step 4: 构建生成提示词
```markdown
你是一位专业的A股复盘写手，擅长撰写散户易懂的每日复盘文章。

## 今日数据

### 大盘指数
- 上证指数：{sh_close}（{sh_pct}%），成交额{sh_amount}亿
- 深证成指：{sz_close}（{sz_pct}%），成交额{sz_amount}亿
- 创业板指：{cy_close}（{cy_pct}%）
- 两市总成交额：{total_amount}亿（较昨日{volume_change}%）

### 资金流向
- 北向资金净流入：{north_flow}亿
- 主力资金净流入：{main_flow}亿
- 行业资金流入Top3：{inflow_top3}
- 行业资金流出Top3：{outflow_top3}

### 板块热点
- 涨幅居前：{top_sectors}
- 跌幅居前：{bottom_sectors}
- 涨停：{limit_up_count}家 / 跌停：{limit_down_count}家

### 关键洞察
{insights}

## 写作要求

### 风格
- 给散户投资者看，通俗易懂，不堆砌专业术语
- 数据说话，每个观点都有数据支撑
- 客观理性，不煽动情绪
- 包含关键数字（涨跌幅、资金额等）

### 结构（严格遵循）
1. **标题**：吸引人但不过分夸张，包含关键数据
   - 例："三大指数集体收涨，北向资金狂买XX亿，A股要变天了？"
   - 例："沪指收跌X%，两市成交额缩量至XXXX亿"

2. **导语**：100-200字，总结当日核心看点

3. **一、大盘回顾**：指数表现+量能分析+涨跌家数

4. **二、资金风向标**：北向资金+主力资金+行业资金轮动

5. **三、热点解读**：板块涨跌+龙头个股点评

6. **四、技术看盘**：支撑/压力位+关键信号

7. **五、明日策略**：方向判断+关注板块+仓位建议

8. **结尾**：风险提示+关注引导

### 字数
- 全文：1200-2000字
- 标题：20-30字
- 每段：不超过5行

### 约束
- 严禁个股推荐
- 不含未来涨跌预测（仅分析可能性）
- 必须包含风险提示
```

### Step 5: 调用AI生成
```python
# 使用通义千问（首选）
response = client_qwen.chat.completions.create(
    model="qwen3-235b",
    messages=[
        {"role": "system", "content": "你是A股复盘写作助手。"},
        {"role": "user", "content": prompt}
    ],
    temperature=0.7
)
```

### Step 6: 后处理
1. **格式检查**：
   - [ ] 5个章节是否完整
   - [ ] 标题是否符合规范
   - [ ] 风险提示是否存在
   - [ ] 数据是否准确（无编造）

2. **去AI味处理**：
   - 检查是否有过度刻板的句式
   - 调整"总之/值得注意的是"等模板用语

### Step 7: 保存草稿
保存到 ~/writing-data/drafts/YYYY-MM-DD-每日复盘.md

```markdown
# 【每日复盘】2026-05-05 A股收盘总结

## 大盘回顾
...

## 资金风向标
...

---

## 元数据
- 生成时间: 2026-05-05 16:30
- 数据日期: 2026-05-05
- AI模型: Qwen3-235B
- 数据源: AKShare + quant引擎
- 审核状态: 待审核
```

---

## 工具链

| 工具 | 用途 |
|------|------|
| terminal | 运行Python脚本计算指标/调用API |
| execute_code | 数据验证和洞察提取 |
| write_file | 保存草稿文件 |
| read_file | 读取原始数据 |

---

## 质量检查清单

发布前验证：
- [ ] 所有指数数据准确
- [ ] 资金流向数据与原始数据一致
- [ ] 板块名称正确
- [ ] 无编造的数据点
- [ ] 风险提示完整
- [ ] 无个股推荐表述
- [ ] 文章结构完整
- [ ] 字数在合理范围

---

## 错误处理

### 数据缺失
1. 标注缺失字段（"数据暂缺"）
2. 调整文章结构（跳过缺失章节）
3. 通知用户数据不完整

### 生成质量差
1. 数据不准确 → 重新生成+强化数据约束
2. 结构不完整 → 使用模板强制填充
3. AI味过重 → 增加去AI后处理

### API失败
1. 切换模型（Qwen3→DeepSeek）
2. 简化生成（仅生成部分章节）
3. 降级为数据报告（不生成AI文章）
