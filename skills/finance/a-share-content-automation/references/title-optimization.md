# 标题优化系统参考文档

创建日期: 2026-05-14
模块路径: ~/writing-data/scripts/title_optimizer.py

## 设计目标
统一A股写作管线标题质量，提高微信公众号打开率（从1-2% → 目标5%+）。

## 架构
```
title_optimizer.py (共享模块, 零AI成本)
├── get_title_templates(draft_type) → 6/4/4类高CTR公式注入AI Prompt
├── score_title(title, draft_type) → 后处理评分 0-100
├── generate_quant_weekly_title(...) → 量化周报专用(模板+数据驱动)
├── is_bad_title(title, draft_type) → 快速检测
└── format_title_feedback(title, draft_type) → 可读反馈
```

## 集成方式

### 方式1: AI Prompt注入 (generate_review/generate_review_seo/weekly_summary)
```python
from title_optimizer import get_title_templates
title_templates = get_title_templates("daily")  # or "weekly"
prompt = f"""...
## 🔥 标题铁律（必读！）
{title_templates}
..."""
```
AI看到6大类高CTR公式，根据当日数据自主选择。

### 方式2: 程序化生成 (quant_weekly — 零AI成本)
```python
from title_optimizer import generate_quant_weekly_title
title = generate_quant_weekly_title(
    sh_chg=1.2, hot_sector="通信设备", mf_total=150,
    top_sectors=[("通信设备",3), ("通用设备",2)]
)
# → "主力一周加仓150亿，上证涨1.2%——钱去哪了？"
```
6种模板+数据驱动，优先短标题+情绪钩子。

### 方式3: 后处理检查 (generate_popular)
```python
from title_optimizer import score_title
score, warnings, verdict = score_title(title, "popular")
if verdict in ("bad", "weak"):
    print(f"⚠️ 标题质量: {verdict} ({score}/100)")
```

## 评分维度
| 维度 | 权重 | 规则 |
|:--|:--|:--|
| 长度 | 30分 | daily:15-35字 ideal; <5字=0分 |
| 数字 | 25分 | 含数字=25分; 无=0分 |
| 情绪钩子 | 25分 | 3+=25分; 2=18分; 1=10分 |
| 死板惩罚 | -20分 | 日期开头/方括号/媒体腔 |
| SEO关键词 | 10分 | 含涨停/主力/上证等≥2=10分 |
判定: ≥70=good, ≥50=acceptable, ≥30=weak, <30=bad

## 已验证的高CTR公式

### 每日复盘 (6类)
1. 数字冲击型 — "一天蒸发3000亿！这个板块..."
2. 反差悬念型 — "主力跑了319亿，A股却在涨？"
3. 问题代入型 — "今天被洗出去了吗？"
4. 数据对比型 — "涨停数骤降到17家，昨天58家"
5. 板块聚焦型 — "这个板块涨了6.8%，90%的人没注意"
6. 反常识揭秘型 — "你以为普涨？实际只有40%股票在涨"

### 周总结 (4类)
1. 主线提炼型 — "这周A股只干了一件事：抱团XXX"
2. 数据震撼型 — "XXX板块5天涨23%，上次是2024年"
3. 散户心态型 — "这周你赚了吗？80%人跑输大盘"
4. 资金方向型 — "主力本周偷偷买什么？"

### 科普 (4类)
1. 痛点问答型 — "新手如何看K线？搞懂3根就够了"
2. 反常识型 — "90%散户不知道：涨停板最危险"
3. 场景代入型 — "你有没有遇到过..."
4. 极简承诺型 — "炒股只看这1个指标就够了"

## 实测案例
| 标题 | 评分 | 判定 |
|:--|:--|:--|
| "K线" | 0/100 | ❌ bad |
| "量化周报 | 上证涨1.2% | ..." | 63/100 | ⚠️ acceptable |
| "2026-05-13 A股每日复盘" | 40/100 | 🔶 weak |
| "一家1.4万亿公司突然涨停..." | 85/100 | ✅ good |
| "主力一周加仓150亿，上证涨1.2%——钱去哪了？" | 90/100 | ✅ good |
| "主力资金跑了319亿，A股今天却在涨？" | 90/100 | ✅ good |
| "【本周热门】通用设备三连活跃..." | 28/100 | ❌ bad |

## 踩坑记录
- 中文全角问号 `？`(\uff1f) ≠ 英文半角 `?` — has_hook检测必须同时检查两种
- `candidates.sort(reverse=True)` 会使短标题排在长标题后面 — 需正向排序+优先值设计
- 量化周报的"数字冲击型"模板(含4段data拼接)天然最长，容易排挤其他模板 — 通过排序函数压低
