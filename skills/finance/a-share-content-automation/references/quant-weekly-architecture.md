# 量化周报架构文档

`quant_weekly.py` — 周日 15:30 自动生成 A 股量化周报，与每日复盘/周总结互补。

## 定位

与 `weekly_summary.py`（热点板块深度分析，AI 写作, 1800-2800 字）互补：
- **quant_weekly.py**: 偏量化信号分析，聚焦多因子模型/缠论/资金流/轮动/风险预警，模板化生成（零 AI 成本），1200-1800 字
- **weekly_summary.py**: 偏市场叙事，聚焦热门前三板块深度解读，DeepSeek AI 写作，1800-2800 字

## 数据源优先级

| 优先级 | 数据 | 来源 | 容错 |
|--------|------|------|------|
| 1 | 每日行情数据（指数/板块/资金流/涨跌停） | `all_data.json` | ≤3 天跳过 |
| 2 | 多因子 + 缠论信号 | `signal_engine.today_signal()` (subprocess, quant_env) | 超时 300s→标注不可用 |
| 3 | 缠论二买独立统计 | `chan_buy_signal.get_latest_signals()` (subprocess) | 超时 120s→标注不可用 |

## 章节结构（7 节）

```
一、多因子信号周度变化       — signal_engine 输出: 总量/L1+/二买/综合>50/行业集中度/周度对比
二、缠论买卖点统计           — chan_buy_signal: 触发数/行业分布/平均得分/周度对比
三、主力资金周度流向模型     — all_data.json: 合计方向+强度/日度轨迹/方向一致性
四、行业轮动量化分析         — all_data.json: 离散度(轮动速度)/高频领涨/持续弱势/持续性解读
五、风险预警信号             — 6 类规则: 背离/缩量/主力流出/跌停比/轮动加速/资金连续流出
六、量化模型综合研判         — 4 维多空矩阵→整体偏向判定
七、关注方向                 — 基于信号+风险提炼 3-5 条观察要点
```

## 关键设计决策

### 1. 零 AI 成本模板化
与 daily review / weekly summary 不同，量化周报不使用 DeepSeek。所有内容由 Python 模板 + 数据填充生成。
原因：量化信号统计是结构化数据，不需要叙事能力；模板更可控，不会出现 AI 幻觉；降低 cron 故障点。

### 2. subprocess 调用 quant_env
`signal_engine.py` 依赖独立的 `quant_env`（含 pandas/numpy/akshare），无法在 writing-domain 的 Python 环境中直接 import。
解决方案：用 `subprocess.run([quant_python, '-c', inline_script])` 执行内联 Python 代码，输出 JSON 统计结果。
超时保护：signal_engine 300s，chan_buy_signal 120s。

### 3. scrub_ai_vocabulary 内联副本
为了 cron 可靠性（避免循环导入 writing-domain 脚本），`quant_weekly.py` 内联了一份 `scrub_ai_vocabulary()`。
风险：三份独立副本（quant_weekly / weekly_summary / generate_review）的 Tier1 词表可能漂移。
缓解：每次修改任何一份的替换词表时，检查另外两处。

### 4. push_to_wechat 复用 publish_draft.py
动态 `sys.path` 注入 + `import publish_draft as pub`，复用其 `get_wechat_token()` / `push_to_wechat_draft()` / `md_to_wechat_html()` / `extract_title()` / `extract_digest()`。
量化周报无图表，跳过图片上传步骤。

### 5. 周度快照存档
每次生成后保存 `~/writing-data/quant-weekly-archive/YYYY-MM-DD-snapshot.json`，包含信号数/二买数/主力方向/轮动得分。
下周运行时自动加载最近快照，实现信号数量/缠论二买数的周度对比。

## 跨脚本依赖图

```
quant_weekly.py
  ├── 读取 all_data.json (collect_data.py 产出)
  ├── 子进程调用 signal_engine.py (quant_env)
  ├── 子进程调用 chan_buy_signal.py (quant_env)
  ├── 内联 scrub_ai_vocabulary() (与 weekly_summary.py 同源但独立)
  └── 动态导入 publish_draft.py (get_wechat_token, push_to_wechat_draft, md_to_wechat_html)
```

## CLI

```bash
python3 quant_weekly.py                     # 默认本周日
python3 quant_weekly.py --date 2026-05-10   # 指定日期
python3 quant_weekly.py --no-push           # 仅生成不推送
python3 quant_weekly.py --dry-run           # 预览（终端输出，不保存不推送）
```

## Cron

```
Job ID: bc02d5952723
Schedule: 30 15 * * 0 (每周日 15:30)
Enabled: true
Deliver: local
```
