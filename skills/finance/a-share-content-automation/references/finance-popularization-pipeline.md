# 理财科普系列管线

2026-05-09 搭建，作为公众号增长的第二内容形态（与 SEO 复盘管线并行）。

## 脚本

`~/writing-data/scripts/generate_popular.py`

## 用法

```bash
# 生成并推送
python3 generate_popular.py --topic "k线"

# 仅生成本地文件，不推送
python3 generate_popular.py --topic "基金定投" --no-push

# dry-run（仅打印 prompt）
python3 generate_popular.py --topic "新手亏钱" --dry-run
```

## 预设选题

| `--topic` 参数 | 标题 |
|---------------|------|
| `k线` | 新手如何看K线？其实搞懂这3根就够了 |
| `基金定投` | 基金定投还是买股票？你的钱到底适合哪种 |
| `主力资金` | 主力资金到底怎么看？别再被数字忽悠了 |
| `市盈率` | 市盈率是什么？买股票前先看这个指标 |
| `涨停` | 涨停和跌停是怎么回事？新手必知的交易规则 |
| `新手亏钱` | 新手炒股最容易亏钱的5个操作 |
| `追涨` | 为什么你一买就跌一卖就涨？ |

## pipeline 触发器

注册于 `pipe-20260509-042221`，4-stage 管线：

1. **生成第一篇**（已完成 5/9）：`--topic k线` → 文件 + 草稿箱
2. **WAIT 3天** → 等第二篇发布窗口
3. **生成第二篇**：`--topic 基金定投` → 文件 + 草稿箱
4. **WAIT 3天** → 等第三篇发布窗口
5. **生成第三篇**：`--topic 主力资金` → 文件 + 草稿箱
6. **L3 决策**：评估科普系列效果

## 模板

`~/writing-data/templates/finance-popularization-template.md`

## 发布流程（2026-05-10 更新）

科普文章没有 `publish_draft.py --type` 参数支持（该脚本只认 `daily` 和 `weekly`）。有两种发布路径：

### 路径A：`publish_kepu.py`（新建，复用 publish_draft.py 核心函数）

**脚本位置**：`~/writing-data/scripts/publish_kepu.py`
**创建时间**：2026-05-10

**流程**：
1. 读取草稿 MD → 提取标题/摘要
2. 获取 WeChat token（遇 40164 IP白名单错误 → 自动降级保存本地HTML）
3. 上传4张配图到微信素材库（token 有效时）
4. 生成封面图并上传
5. 推送到公众号草稿箱

**用法**：
```bash
# 直接发布
~/tools/quant_env/bin/python3 scripts/publish_kepu.py
```

**已知问题**（当前）：
- 服务器IP（113.117.56.38）不在微信IP白名单 → 持续 40164 错误
- 已自动降级为本地HTML保存到 `~/writing-data/published-html/YYYY-MM-DD-科普.html`
- QQ Bot P0通知已配置自动发送

**IP白名单修复后重新发布**：
```bash
# 先加白 IP（mp.weixin.qq.com → 开发 → 基本配置）
# 重新运行即可
~/tools/quant_env/bin/python3 scripts/publish_kepu.py
```

### 路径B：`browser_publish.py`（Playwright 浏览器自动化）

绕过IP白名单，Cookie鉴权，不依赖 `access_token`。详见 `references/wechat-mp-prosemirror-publishing.md`。

### 路径C：降级本地HTML（最终兜底）

保存到 `~/writing-data/published-html/`，手动复制到公众号编辑器。

## 已知坑

### push_draft() 返回值未检查 → 草稿箱空

**已修复 (2026-05-09)**: 原脚本调用 `push_draft()` 不检查返回值，推送失败时只打 warning 不中断。已加 3 次重试 + 结果校验。详见 SKILL.md 的 `❌ 生成脚本的 push_draft() 返回值必须检查` 节。

### 文章重复生成（hash slug 不同）

每次运行 `--topic k线` 会调用 DeepSeek 生成不同内容，`ascii_slug` 基于 `hash(title) % 10000` 生成不同后缀 → 多个不同内容的文件。这是预期行为（每次内容不同），但注意草稿箱会多一条。

### ❌ 文章必须配图，纯文字读者不买账

**2026-05-09 用户纠正**: 科普文章不能只有文字。每篇文章必须包含对应的示意图：
- K线主题 → K线结构图（实体/影线标注）+ 红绿对比图 + 趋势方向图
- 均线主题 → K线+均线示例图
- 每个章节对应的配图需内嵌在正文段落之后

**生成方式**: 用 PIL 绘制（无需 matplotlib，系统 PIL 已装）。图片保存到 `CHARTS_DIR / date_str /`，markdown 中用 `![说明](charts/xxx.png)` 格式引用（注意：路径是 `charts/xxx.png` 而非 `charts/YYYY-MM-DD/xxx.png`，因为 `publish_draft.py` 的 `extract_chart_references()` 会自动补 `date_str` 目录）。

### ❌ markdown 图片路径必须适配 `extract_chart_references()`

`extract_chart_references()` 正则匹配 `!\[.*\]\((charts/[^)]+)\)` 然后自动补成 `CHARTS_DIR / date_str / 文件`。所以 markdown 里的路径要写成：
- ✅ `charts/kline_structure.png`（正确：解析为 `~/writing-data/charts/2026-05-09/kline_structure.png`）
- ❌ `charts/2026-05-09/kline_structure.png`（错误：解析为 `~/writing-data/charts/2026-05-09/2026-05-09/kline_structure.png`）

### ❌ AI 味太重需要后处理

**2026-05-09 用户纠正**: DeepSeek 生成的科普文章有显著 AI 痕迹：
- 开头 "好的，没问题！" — 经典 chatbot 痕迹
- 多用 "总而言之"、"记住" 等模板句式
- 整体偏教科书口吻，不够自然

**处理方式**: 通过 `avoid-ai-writing` skill 手动清洗。关键修改点：
1. 删除开头 chatbot 痕迹（"好的，没问题！"、"让我们" 等）
2. 替换模板句式（"总而言之"→直接结论）
3. 去掉生硬的"标题：XXX" 式标记，直接用正文段落过渡
4. 让语言更像朋友聊天，少教科书感

### ❌ 标题格式不规范

`generate_popular.py` 自带的 `push_draft()` 函数（脚本内嵌版本）HTML 转换简单。h1(`# `) 被转为 `<h2>`。正文中不应出现 `### 标题：` 这种冗余标记，标题直接用 `h1`（一个 `# ` 前缀），section 标题用 `## ` 前缀。

### ❌ 封面图字体需验证

系统字体路径（`/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc`）在 PIL 下工作正常。但不同环境可能字体缺失或路径不同，需要用 `font_candidates` 列表逐个尝试。
