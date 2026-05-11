# matplotlib/mplfinance 中文字体渲染

## 问题

Ubuntu 上 matplotlib 图表中文显示为方框或空格。即使 `rcParams['font.sans-serif']` 设置了中文字体，mplfinance 也不继承该设置。

## 根因

1. mplfinance 的 `mpf.plot()` 使用独立样式系统，不从 `plt.rcParams` 获取字体
2. `plt.rcdefaults()` 会重置所有 rcParams（包括字体设置）
3. 字体缓存过期后需要重建
4. **`.ttc` (TrueType Collection) 字体文件 — matplotlib FreeType 后端无法正确提取字形**。字体名称在 `fontManager.ttflist` 中被列出，`findfont()` 也能找到路径，但实际渲染时 glyph 全部回退到 DejaVu Sans，导致中文显示为空格（0% 文字密度）。`fc-list` 和 `fontconfig` 可以使用 `.ttc`，但 matplotlib 不行。

## 解决方案

### 安装中文字体
```bash
sudo apt install fonts-wqy-zenhei
```

### ⚠️ TTC 字体 matplotlib 渲染失败（2026-05-06 诊断）

系统通过 `fonts-wqy-zenhei` 安装的是 `.ttc` (TrueType Collection) 文件，matplotlib 可枚举但 **无法提取字形**，所有中文渲染为空（像素密度 0%）。

**正确方案：提取为单 .ttf**：
```bash
python3 -c "
from fontTools.ttLib import TTCollection
tt = TTCollection('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc')
tt.fonts[0].save(os.path.expanduser('~/.fonts/wqy-zenhei.ttf'))
"
```

然后在代码中使用：
```python
from matplotlib.font_manager import FontProperties
fp = FontProperties(fname='/home/pebynn/.fonts/wqy-zenhei.ttf', size=16)
ax.set_title('中文标题', fontproperties=fp)
```

### 渲染验证方法（程序化像素检测）

```python
from PIL import Image
import numpy as np
arr = np.array(Image.open('chart.png'))
rgb = arr[:,:,:3]  # ⚠️ 只用RGB，忽略Alpha通道
title_region = rgb[5:50, 100:400, :]
dark = np.sum(np.all(title_region < 60, axis=2))
total = title_region.shape[0] * title_region.shape[1]
density = dark / total * 100
print(f"Text density: {density:.2f}%")  # >0.5% = 正常渲染
```

### 致命陷阱

- `fontname=` 参数依赖 fontconfig 匹配，不可靠 → 必须用 `fontproperties=FontProperties(fname=...)`
- `ax.set_title()` vs `fig.suptitle()` — mplfinance 前者无效
- `legend(fontproperties=fp)` — 错误 → `legend(prop=fp)` 正确
- 像素检测用 `arr[:,:,:3]` (RGB)，不是 `arr` (RGBA) — RGBA 会永久返回 0%

### 关键步骤：从 TTC 提取单 TTF

如果系统只有 `.ttc` 格式中文字体（`/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc` 含 3 个字体面），必须提取为单 `.ttf`：

```python
from fontTools.ttLib import TTCollection
import os

home = os.path.expanduser('~')
os.makedirs(f'{home}/.fonts', exist_ok=True)
tt = TTCollection('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc')
tt.fonts[0].save(f'{home}/.fonts/wqy-zenhei.ttf')
# 然后重建 matplotlib 字体缓存：删除 ~/.cache/matplotlib/
```

**验证 TTF 是否生效**：
```python
from matplotlib.font_manager import FontProperties, fontManager
# 显式添加
fontManager.addfont(os.path.expanduser('~/.fonts/wqy-zenhei.ttf'))
fontManager._load_fontmanager(try_read_cache=False)
# 然后使用 FontProperties(family='WenQuanYi Zen Hei')
```

**验证渲染正确性**：不要信任视觉检查 — 用像素密度检测：
```python
from PIL import Image
import numpy as np
arr = np.array(Image.open('chart.png'))
rgb = arr[:,:,:3]  # 丢弃 alpha 通道！
title = rgb[5:60, 100:400, :]
dark = np.sum(np.all(title < 50, axis=2))
total = title.shape[0] * title.shape[1]
# density > 0.5% 说明文字在渲染
```

### 清除字体缓存
```bash
rm -rf ~/.cache/matplotlib/ ~/.matplotlib/
```

### 代码方案：FontProperties 显式指定

不要依赖 rcParams。对每个中文文本元素使用 `FontProperties`:

```python
from matplotlib.font_manager import FontProperties, findfont

def get_font_properties():
    font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
    return FontProperties(fname=font_path)

fp = get_font_properties()

# 普通 matplotlib
ax.set_title("中文标题", fontproperties=fp)
ax.set_xlabel("横轴", fontproperties=fp)
ax.legend(prop=fp)  # 图例用 prop= 而非 fontproperties=

# mplfinance — 使用 fig.suptitle()
fig, axes = mpf.plot(..., returnfig=True)
fig.suptitle("中文标题", fontproperties=fp)

# mplfinance 的 ylabel 需要用 fontproperties
axes[0].set_ylabel("点位", fontproperties=fp)
```

### 字体路径查找
```python
from matplotlib.font_manager import findfont, FontProperties
fp = FontProperties(family="WenQuanYi Zen Hei")
font_path = findfont(fp)
```

### 🔴 致命陷阱：TTC (TrueType Collection) 渲染失败

**症状**：`FontProperties(fname='wqy-zenhei.ttc')` 能找到字体（`findfont` 返回正确路径），matplotlib fontManager 也列出该字体，但中文字形全部渲染为空（0% 文字密度）。

**根因**：`fonts-wqy-zenhei` 安装的是 `.ttc` 文件（TrueType Collection，含3个字体面）。matplotlib 的 FreeType 后端能加载 TTC 但无法正确从中提取字形，最终回退到 DejaVu Sans（只有拉丁字母）。

**修复**：用 `fontTools` 提取 TTC 为单 `.ttf` 文件：

```bash
python3 -c "
from fontTools.ttLib import TTCollection
import os
home = os.path.expanduser('~')
tt = TTCollection('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc')
os.makedirs(f'{home}/.fonts', exist_ok=True)
tt.fonts[0].save(f'{home}/.fonts/wqy-zenhei.ttf')  # font 0 = Regular
"
```

然后使用提取的 TTF：
```python
fp = FontProperties(fname=os.path.expanduser('~/.fonts/wqy-zenhei.ttf'))
```

**验证方法 — 注意 RGBA 陷阱**：matplotlib 保存的 PNG 可能是 RGBA（4通道）而非 RGB（3通道）。像素密度检测时只取 RGB 通道：
```python
# ❌ 错误：RGBA 图片用 3 通道阈值 → 永久返回 0%
arr = np.array(Image.open('chart.png'))
dark = np.sum(np.all(arr < 50, axis=2))  # arr有4通道，阈值只有3个 → False

# ✅ 正确：只用 RGB 通道
rgb = arr[:,:,:3]
dark = np.sum(np.all(rgb < 50, axis=2))
```

**统一修复入口**：`generate_charts.py` 的 `setup_chinese_font()` 和 `publish_draft.py` 的 `create_cover_image()` 都需要更新为优先使用提取的 `.ttf`，`.ttc` 作为降级。

### 字体已知不一致点

- `generate_charts.py`：使用 `FontProperties(fname=字体路径)` ✅ 正确
- `publish_draft.py` 封面图：原用 `fontname=font_name` → 已修复为 `fontproperties=FontProperties(fname=...)` ✅（2026-05-06）
- `publish_draft.py` 封面图 `fm.findfont(fname)` 调用：未指定 `FontProperties` → 可能在某些环境下失败。已修复为 `fm.findfont(FontProperties(family=fname))`

## 关键陷阱

- `.ttc` (TrueType Collection) 字体 matplotlib 无法渲染 — 须提取为单 `.ttf`
- `axes[0].set_title()` 对 mplfinance 无效，必须用 `fig.suptitle()`
- `legend(fontproperties=fp)` ❌ → `legend(prop=fp)` ✅
- `plt.rcdefaults()` 会清除字体设置，不要在字体配置后调用
- `fontname=` 参数不可靠（依赖 fontconfig），必须用 `fontproperties=FontProperties(fname=...)`
- 像素检测字体渲染须用 `arr[:,:,:3]`（RGB），RGBA 会误报 0%

### .ttc → .ttf 提取

系统安装的中文字体大多为 .ttc（如 wqy-zenhei.ttc 含3个字体面），matplotlib FreeType 后端无法渲染。需用 fontTools 提取为单 .ttf：

```bash
python3 -c "
from fontTools.ttLib import TTCollection
tt = TTCollection('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc')
tt.fonts[0].save(os.path.expanduser('~/.fonts/wqy-zenhei.ttf'))
"
```

提取后 matplotlib 自动识别 `~/.fonts/` 目录，`FontProperties(fname=path)` 正常渲染。
- **TTC 文件渲染失败** → 提取为单 TTF，见上方"致命陷阱"章节
- **RGBA 通道误判** → 像素密度检测只取 `[:,:,:3]`，见上方验证方法

### fontname= vs FontProperties — 看似可用实则脆弱

`ax.text(..., fontname='WenQuanYi Zen Hei')` 使用 matplotlib 的 fontconfig 匹配。在 fontconfig 缓存正常时有效，但以下情况会失败：
- fontconfig 缓存过期或损坏
- matplotlib fontManager 重建后字体名称变化
- 多用户环境下 fontconfig 配置不同

**正确做法**：始终使用 `FontProperties(fname=字体文件路径)` 直接指向字体文件：
```python
# ❌ fontconfig-based — 不可靠
ax.text(100, 200, "中文文本", fontname="WenQuanYi Zen Hei")

# ✅ 直接文件路径 — 最稳健
from matplotlib.font_manager import FontProperties
fp = FontProperties(fname="/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
ax.text(100, 200, "中文文本", fontproperties=fp)
```

### 渲染改动必须实际验证，禁止只看代码

修改字体/配色代码后，只检查代码逻辑或 hex 值就声称"已修复"是**假信号**。必须：
1. 实际运行脚本生成 PNG
2. 像素采样或肉眼确认中文是否正确显示
3. 确认旧缓存 PNG 已被覆盖或删除

验证命令：
```bash
# 生成测试图
python3 -c "
import matplotlib; matplotlib.use('Agg')
from matplotlib.font_manager import FontProperties
import matplotlib.pyplot as plt
fp = FontProperties(fname='/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', size=16)
fig, ax = plt.subplots()
ax.set_title('中文字体渲染测试', fontproperties=fp)
fig.savefig('/tmp/font_test.png'); plt.close()
"
# 检查渲染区域像素填充率（>1% 表示文字被渲染）
python3 -c "
from PIL import Image; import numpy as np
arr = np.array(Image.open('/tmp/font_test.png'))
center = arr[100:300, 100:500]
fill = np.sum(np.any(center < 200, axis=2)) / (center.shape[0]*center.shape[1]) * 100
print(f'Font render fill: {fill:.1f}% (\" + (\"OK\" if fill > 1 else \"FAIL - check font\") + \")')
"
