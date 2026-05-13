# generate_popular.py v5.1 升级 (2026-05-13)

## 背景

用户反馈写作管线产出太死板，配图不足且不与内容呼应。要求对标5月10日"K线图怎么看"质量标杆。

## 改动矩阵

| 维度 | v5.0 (旧) | v5.1 (新) |
|------|-----------|-----------|
| build_prompt() | 空壳模板，无质量锚点 | 注入K线科普质量标杆 + 去AI化指令 |
| 内容配图 | 仅封面图 | 9种主题→matplotlib配图，每篇2-3张自解释图表 |
| 后处理 | scrub_ai_vocabulary() 26词 | humanize_content(): 泄漏清理+AI词替换+图片修复+标题去重 |
| 管线流程 | 写作→后处理→封面 | **配图→写作→后处理→封面** |
| 图片引用 | LLM自由发挥 | build_prompt注入图片清单，LLM在文中对应位置插入引用 |

## 新增函数

### generate_content_images(topic_key, date_str)
遍历 `TOPIC_IMAGE_MAP[topic_key]`，为每个图片类型调用 `_render_single_image()`，返回生成的图片文件名列表。

### _render_single_image(img_type, topic_key, out_path)
使用 `/home/pebynn/tools/quant_env/bin/python3` 执行matplotlib脚本，生成单张配图。暗色主题(#0d1117)，DPI 200。

### TOPIC_IMAGE_MAP
9种选题→图片类型映射：
```python
TOPIC_IMAGE_MAP = {
    "K线": ["kline_example", "kline_structure", "kline_red_green"],
    "均线": ["kline_example", "ma_cross"],
    "基金定投": ["dca_chart", "risk_pyramid"],
    "主力资金": ["capital_flow_bar", "capital_flow_pie"],
    "市盈率": ["pe_comparison", "pe_distribution"],
    "追涨": ["chase_up_risk", "kline_example"],
    "新手亏钱": ["five_mistakes", "risk_pyramid"],
    "涨停跌停": ["limit_up_down_structure", "kline_red_green"],
}
DEFAULT_IMAGES = ["kline_example", "kline_structure"]
```

### humanize_content(text)
三层后处理：scrub_template_leakage() → scrub_ai_vocabulary() → 图片修复+标题去重

### scrub_template_leakage(text)
清除LLM输出的模版泄漏碎片：
- "一、二、三" 教科书式结构
- "AI辅助创作" 标签残留
- "⚠️" "📌" 等prompt格式泄漏
- "## 写作模板" 等prompt指令泄漏
- "好的/没问题/咱们来聊聊" 等开场白

## build_prompt() 质量注入

```python
def build_prompt(topic_title, topic_key, image_list):
    # 注入质量标杆（K线科普）
    # 注入写作模板
    # 注入图片引用指令

## 质量标杆：这篇K线科普是满分标准
标题「新手如何看K线？其实搞懂这3根就够了」—— 问题式+数字+悬念。
开头「你有没有遇到过这种情况：打开股票软件，满屏红红绿绿的柱子...」
正文把K线比喻成"小房子"、多空是"拔河比赛"...
关键：读起来不像财经文章，像有经验的朋友在聊天。
```

## 致命坑点

### 1. F-string嵌套NameError
`_render_single_image()` 中 render_script 是外层 f-string，内部 `{i+1}` `{m}` 等变量被外层消耗 → NameError。
**修复**: `f"{i+1}. {m}"` → `str(i+1)+". "+m`

### 2. 图片引用被代码块包裹
LLM输出 `\`\`\` ![image](charts/x.png) \`\`\`` → 不渲染为图片。
**修复**: `humanize_content()` 中正则去除包裹。

### 3. 标题重复
`md_content = f"# {title}\n\n{content}"` + LLM也输出 `# title` → 两个H1。
**修复**: `humanize_content()` 中检测并合并连续H1标题。

### 4. 图片未全部引用
LLM可能只引用部分图片。prompt必须强调"每张配图必须出现，对应内容之后"。

## 干跑验证

```bash
# 均线选题: 2张配图生成 + DeepSeek 2020字 + 无AI套话 ✅
python3 generate_popular.py --topic 均线 --no-push

# 市盈率选题: 2张配图 + DeepSeek 1703字 + 图片正确嵌入 ✅
python3 generate_popular.py --topic 市盈率 --no-push
```

## Cron影响

cron `11502faaf718` (每日18:00科普) 自动使用新版，无需修改cron配置。
