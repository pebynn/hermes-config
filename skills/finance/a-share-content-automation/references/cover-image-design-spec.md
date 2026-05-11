# 封面图设计规范 v2.0

基于 baoyu-infographic 的 dashboard + corporate-memphis 设计语言，matplotlib 纯渲染。

## 布局 (900x500px)

```
┌──────────────────────────────────────────────────┐
│ y=430-500  顶部指标条 (#161b22 底)                  │
│  上证 ▲0.11%  深证 ▼0.09%  创业板 ▼0.27%  科创50 ▲5.19% │
│                                        成交 2.74万亿│
├──────────────────────────────────────────────────┤
│ y=300-430  主标题区                                 │
│                                                    │
│         ═══════ 金色装饰线 ═══════                  │
│              A股每日复盘          (34pt bold white) │
│              2026-04-30           (16pt gray)       │
│                                                    │
├──────────────────────────────────────────────────┤
│ y=30-110   底部数据卡片 (#161b22 底, #30363d 边框)    │
│   涨停 78    跌停 9    主力 -520亿    最热 燃料电池 +9.46% │
│   (红22pt)   (绿22pt)   (绿22pt)       (金22pt)      │
├──────────────────────────────────────────────────┤
│ y=0-30    数据来源: AKShare | 东方财富  (9pt #484f58) │
└──────────────────────────────────────────────────┘
```

## 配色方案

| 元素 | 色值 | 用途 |
|:-----|:-----|:----|
| `#0d1117` | 全局背景 | GitHub 暗色主题 |
| `#161b22` | 卡片背景 | 指标条、数据卡片 |
| `#e6edf3` | 主文字 | 标题、数据值 |
| `#8b949e` | 次文字 | 标签、副标题 |
| `#ff4444` | 红色 | 上涨、涨停 |
| `#00c853` | 绿色 | 下跌、跌停、资金流出 |
| `#ffb347` | 金色 | 装饰线、热门板块高亮 |
| `#30363d` | 分隔线 | 数据卡片边框 |
| `#484f58` | 极淡灰 | 底部来源文字 |

## 数据读取

从 `~/writing-data/raw/{date}/all_data.json` 读取：

```python
market_data = {
    "上证": {"pct": 0.11},
    "深证": {"pct": -0.09},
    "创业板": {"pct": -0.27},
    "科创50": {"pct": 5.19},
    "_turnover": 27409.12,       # market.total_turnover
    "_main_force": -520.29,      # capital_flow.main_force.net_inflow
    "_limit_up": 78,             # limit_up_down.limit_up.total
    "_limit_down": 9,            # limit_up_down.limit_down.total
    "_hot_sector": "燃料电池",    # sectors.industry[0].name
    "_hot_pct": 9.46,            # sectors.industry[0].change_pct
}
```

## 降级行为

数据文件不存在时 → 仍生成骨架封面（仅标题+日期，无数据卡片和指标条）
matplotlib 不可用时 → 返回 None，不影响主发布流程

## 验证方法

```bash
python3 -c "
from publish_draft import create_cover_image
create_cover_image('2026-04-30', 'daily')
"
ls -la ~/writing-data/charts/2026-04-30/cover.png
# 期望: 956x530px, 70-80KB, RGBA
```
