# 写作管线根因审计 — 2026-05-08

## 问题：为什么同样的问题反复修不好

### 根因1：函数3份拷贝，永远差一截

关键函数写了N份，独立锁在各自脚本里：

| 函数 | 文件数 | 文件列表 |
|:--|:--:|:--|
| `safe_float()` | 7 | collect_data, fallback_pipeline, generate_charts, generate_review, morning_brief, quant_weekly, weekly_summary |
| `scrub_ai_vocabulary()` | 3 | generate_review, weekly_summary, quant_weekly（阉割版，无Tier2/Tier3） |
| `call_deepseek()` | 2 | generate_review, weekly_summary |
| `post_process_pipeline()` | 2 | generate_review, weekly_summary |
| `detect_ai_clusters()` | 2 | generate_review, weekly_summary |
| `get_week_dates()` | 2 | weekly_summary, quant_weekly |
| `aggregate_weekly_data()` | 2 | weekly_summary, quant_weekly |

每次修复只改了一个文件，其他文件从来不同步。同样问题换个脚本再犯一次。

### 根因2：82KB SKILL.md ≈ 没人读

- SKILL.md: 82,305 字节
- reference 文件: 46 个
- 每个reference对应一次历史bug修复

文件太大 = 每次修bug时不翻reference，翻也翻不完。所以同样的bug换个脚本换种形式再出现。

典型案例链：
1. `data_completeness` 无条件True → collect_data.py 修了 → fallback_pipeline.py 同样问题没修
2. 涨跌家数推断 → generate_review.py 删了 → weekly_summary.py 没查过
3. `requests.post(json=body)` unicode转义 → publish_draft.py 修了 → generate_review.py 和 weekly_summary.py 事后才发现

### 根因3：数据管线无契约

管线 collect→charts→review→publish 之间没有"数据够不够用才往下传"的门禁。今天 `data_completeness` 里 sectors=false, main_force_flow=false，图表少出2张，publish照样跑，发出去的文章缺板块数据。

### 根因4：每次修症状不修结构

半个月内写了十几个"已修复"，每个修复都是改一行/删一行，从未改动过"3份代码"这个结构本身。症状修好了，结构还在，下个bug换个脚本出现。

## 修复方向：data_guard.py 五层守门员

详见 `data-accuracy-layer` skill。

核心改动：
1. **共享字段映射** — 全管线只在一处定义 Sina parts[]/东财 f43/f170
2. **采集时交叉验证** — 写入前多源对比+异常值拦截
3. **图表质量门禁** — 生成后检查文件存在+文件大小+最少张数
4. **内容交叉验证** — 文章每个数字追溯原始数据，找不到源就block
5. **函数漂移检测** — 启动时扫描同名函数hash，不一致就警告

## 脚本生态总览

```
写作域(14):  collect_data.py, generate_charts.py, generate_review.py,
             weekly_summary.py, publish_draft.py, morning_brief.py,
             fallback_pipeline.py, audit_guard.py, publish_audit_guard.py,
             quant_weekly.py, publish_to_xueqiu.py, cookie_publish.py,
             browser_publish.py, pipeline_health_check.py

量化域(39):  daily_kline_update.py, signal_engine.py, data_common.py,
             xueqiu_kline.py, kline_fallback.py, precache_kline.py, ... (39个)

共享模块:    ~/quant/xueqiu_kline.py (14KB), ~/quant/data_common.py (39KB)
```
