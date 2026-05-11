# 图表生成与微信发布参考

writing-domain 图表生成管线（2026-05-05 验证）。

---

## 4张分析图表

| 图表 | API调用 | 关键参数 |
|:--|:--|:--|
| K线图 | `ak.stock_zh_index_daily_em("sh000001").tail(60)` | mplfinance `type="candle"` + MA5/10/20 |
| 热力图 | `all_data.json` sector数据 | matplotlib `barh` + 颜色编码 |
| 资金流 | `ak.stock_hsgt_hist_em("北向资金").tail(20)` | 双轴: bar(日净流入) + line(累计) |
| 分布图 | `ak.stock_zh_a_spot_em()` | 全A个股 histogram + 涨跌停阈值线 |

## 中文字体陷阱

**核心问题**：mplfinance 不继承全局 rcParams，且 `plt.rcdefaults()` 会重置所有参数。四种独立的文本渲染路径都需要分别处理。

### 正确方案（3层防御）

**第1层 — rcParams（基础覆盖）**：
```python
plt.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei", "DejaVu Sans"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei", "DejaVu Sans"]
```
**注意**：`plt.rcdefaults()` 后必须重新设置 — 永远不要在设置 rcParams 后调用它。

**第2层 — FontProperties（最可靠）**：
```python
from matplotlib.font_manager import FontProperties
# 找到字体文件路径
fm._load_fontmanager(try_read_cache=False)
font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"  # Ubuntu WenQuanYi
fp = FontProperties(fname=font_path, size=12)
# 每个中文元素都传入 fontproperties=
ax.set_title("标题", fontproperties=fp)
ax.set_ylabel("标签", fontproperties=fp)
ax.legend(..., prop=fp)
ax.text(x, y, "文本", fontproperties=fp)
```

**第3层 — mplfinance 特判**：
```python
# mpf.plot 使用 fig.suptitle() 而非 axes.set_title()
fig, axes = mpf.plot(..., returnfig=True)
fig.suptitle("上证指数近60日走势", fontproperties=fp_title, fontsize=16, fontweight="bold")
# mplfinance 的 addplot 标签放在 legend 中也要用 FontProperties
axes[0].legend(loc="upper left", fontsize=10)  # 纯英文标签不需要
```

### 调试命令
```bash
# 1. 清缓存强制重建
rm -rf ~/.cache/matplotlib/ ~/.matplotlib/

# 2. 确认可用字体
fc-list :lang=zh | head -10
python3 -c "
import matplotlib.font_manager as fm
fm._load_fontmanager(try_read_cache=False)
for f in fm.fontManager.ttflist:
    if 'WenQuanYi' in f.name:
        print(f'{f.name} -> {f.fname}')
"

# 3. 验证渲染（无警告=成功）
python3 -c "
import matplotlib, matplotlib.pyplot as plt
matplotlib.use('Agg')
fp = matplotlib.font_manager.FontProperties(fname='/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc')
fig, ax = plt.subplots()
ax.set_title('中文测试', fontproperties=fp)
fig.savefig('/tmp/test.png')
print('OK')
"
```

### 常见错误

| 症状 | 原因 | 修复 |
|:----|:----|:-----|
| Glyph missing from DejaVu Sans | 某文本元素没设 fontproperties | 检查 title/label/legend/text 全部加 fp |
| plt.title() 无效 | mplfinance 使用 fig.suptitle() | 改用 fig.suptitle(fontproperties=fp) |
| 删除缓存后问题依旧 | fontlist-*.json 重建时还是旧数据 | 先用 rm -rf 删整个 ~/.cache/matplotlib/ |
| 热力图中文正常，K线不正常 | mplfinance 不继承 rcParams | 第2层+第3层 FontProperties |

## 微信图片上传流程

```
1. 获取Access Token (缓存7200s)
2. POST /cgi-bin/material/add_material?access_token=TOKEN&type=image
3. Content-Type: multipart/form-data, 字段名: media
4. 返回: {"media_id":"xxx", "url":"https://mmbiz.qpic.cn/..."}
5. 替换HTML中 <img src="charts/kline.png"> → <img src="https://mmbiz.qpic.cn/...">
```

**错误处理**：
- errcode 40001 → 刷新token重试
- errcode 45009 → API频限，降级本地保存
- 网络错误 → 全部降级，保留本地路径

## 图片交错插入（Interleaving）

publish_draft.py 不再把所有图片堆在文章底部"数据图表" section。改为按章节交错插入：

```
文章结构（转换后）:
<h3>一、大盘回顾</h3>
<p>...</p>
<p><img src="https://mmbiz.qpic.cn/..."/></p>   ← kline.png 插在这里
<p style="color:#888;font-size:13px;text-align:center">上证指数日K线走势</p>

<h3>二、资金风向标</h3>
<p>...</p>
<p><img src="https://mmbiz.qpic.cn/..."/></p>   ← capital_flow.png 插在这里
<p style="color:#888;font-size:13px;text-align:center">北向资金近20日净流入</p>
...
```

**实现**（`interleave_images(html, image_map)`）：
1. 先用 regex 移除旧"数据图表"尾部 section（含 emoji 前缀的 `<h3>📊 数据图表</h3>` → 全部删除）
2. 定义 section→image 映射表：`{章节关键词 → (image_key, caption_text)}`
3. 对每个映射项，查找对应 `<h3>...关键词...</h3>`，在闭合标签后插入 `<img>` + caption
4. 关键词用 `re.escape()` 包裹适配中文，`re.IGNORECASE` 避免大小写问题
5. 图片未上传成功时静默跳过（不插入占位）

**容错**：某个 section 在文章中没有出现时，对应图片不插入也不报错。image_map 为空时直接返回原 HTML。

## 管线验证（端到端）

```bash
date="2026-05-05"
python3 ~/.hermes/profiles/writing-domain/skills/a-share-data-collector/scripts/collect_data.py --date "$date"
python3 ~/.hermes/profiles/writing-domain/skills/a-share-review-writer/scripts/generate_charts.py --date "$date"
python3 ~/.hermes/profiles/writing-domain/skills/a-share-review-writer/scripts/generate_review.py --date "$date"
python3 ~/.hermes/profiles/writing-domain/skills/a-share-publisher/scripts/publish_draft.py --date "$date"
find ~/writing-data -name "*${date}*" | sort
```

预期产出：4张PNG（kline/sector_heatmap/capital_flow/market_breadth） + 1张封面（cover.png） + 1篇MD草稿 + 1个发布日志。

## 封面图 cover.png

publish_draft.py 发布时自动检测 `~/writing-data/charts/YYYY-MM-DD/cover.png`，不存在则用 matplotlib 无头模式生成：

- 深蓝色背景 `#1a1a2e`
- 标题：`YYYY-MM-DD A股每日复盘`（白色 28pt 居中）
- 副标题：`数据来源: AKShare | EastMoney`（银色 14pt）
- 900x500 px, 150 DPI
- 依赖 matplotlib（缺失时静默跳过）

## IP白名单诊断

每次获取 access_token 后自动调用 `cgi-bin/get_api_domain_ip` 检查 errcode=61004。

```bash
# 手动查询服务器公网IP
python3 ~/.hermes/profiles/writing-domain/skills/a-share-publisher/scripts/publish_draft.py --check-ip
```

将查询到的 IP 添加到「微信公众号后台 → 设置与开发 → 基本配置 → IP白名单」。
