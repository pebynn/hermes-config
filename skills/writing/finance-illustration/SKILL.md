---
name: finance-illustration
description: 金融科普配图生成 — 用 matplotlib 生成高清晰度 K线结构图/均线图/趋势图等配图。取代 PIL 手绘制图。
version: "1.0.0"
tags: ["finance", "illustration", "matplotlib", "chart", "wechat"]
---

# Finance Illustration — 金融科普配图生成

## 前置条件

matplotlib 已安装在 quant_env: `/home/pebynn/tools/quant_env/bin/python3`
中文配置: `Noto Sans CJK JP` (实际渲染中文), 或 fallback 到 PIL.

## 通用配置

```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# 确保中文字体
for f in fm.fontManager.ttflist:
    if 'Noto Sans CJK' in f.name:
        plt.rcParams['font.sans-serif'] = [f.name] + plt.rcParams['font.sans-serif']
        break
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 200  # 高DPI确保手机端清晰
```

## 配图模板

### 1. K线结构图 (kline_structure)

展示阴阳线的实体/上影线/下影线结构,红绿对比.

```python
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5), facecolor='#0d1117')
# ... 用 matplotlib.patches.Rectangle 画实体
# ... 用 ax.plot 画影线
# ax.annotate 标注各部分
# DPI 200, 字号 ≥14pt
```

### 2. K线+均线示例图 (kline_example)

用 np.random 生成模拟K线走势, 叠5日/20/60日均线, 标出关键区域.

```python
# 生成模拟价格数据
np.random.seed(42)
close = 100 + np.cumsum(np.random.randn(n) * 0.5)
# 画价格线 + 移动均线
# 标注: "5日均线向上 短期情绪好"等
```

### 3. 趋势判断图 (kline_trend)

用两根趋势线+标注说明上升/下降趋势.

### 4. 红绿对比图 (kline_red_green)

并排两个K线柱子(红+绿), 底部标注含义.

## 关键约束

| 项 | 要求 |
|----|------|
| DPI | ≥200 (手机端750px宽阅读清晰) |
| 标题字号 | ≥16pt |
| 标注字号 | ≥11pt |
| 线宽 | ≥1.5px (细线在手机端不可见) |
| 字体 | Noto Sans CJK JP, 或 wqy-zenhei fallback |
| 背景 | 暗色 #0d1117 或 白色 |
| 边框 | 图/标注加 rounded box 边框提升可读性 |

## 验收标准

生成后检查:
1. 手机屏幕(750px宽)下文字清晰可读
2. 颜色对比明显(红涨绿跌,不混淆)
3. 标注指向明确,不模棱两可
4. 图片体积 < 200KB

## 触发场景

- generate_popular.py 科普文章配图
- 复盘文章新增配图
- 任何需要金融科普类插图的需求

## Python 路径

执行 matplotlib 脚本必须用: `/home/pebynn/tools/quant_env/bin/python3`
(系统 python3 无 matplotlib)
