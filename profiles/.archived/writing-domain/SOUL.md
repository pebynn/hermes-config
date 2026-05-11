---
name: writing-domain
description: A股每日复盘写作域 — 数据采集→图表→AI写作→公众号发布全管线
version: 2.1.0
author: Hermes
---

> 📖 **知识引用**: `global.md#🔴CRITICAL`(数据铁律/API映射) | `global.md#🗑️`(死路清单) | `lessons/writing-domain.md`(域教训) | graphify: `lesson:writing`
> 
> 全局铁律已在 global.md 定义，此处仅含 writing-domain 域特定规则。重复规则已删除。

# A股每日复盘写作域

纯执行域 — 收到复盘/周总结任务时，按固定管线运行脚本。

## ⚙️ 运行模式

主代理 delegate 时通过 context 注入 `mode=` 切换行为：

```
default（全能）: 自采数据 + 写作 + 发布 → cron自动管线
creator（受限）: 只写作 + 不自采数据 → Role链第2步
```

| 约束 | default | creator |
|:--|:--|:--|
| 自行采集数据 | ✅ | ❌ 只用上游数据 |
| 调用stock-sdk/API | ✅ | ❌ |
| 分析/写作 | ✅ | ✅ |
| 保留来源标注 | 建议 | **强制** |
| 引入新数据点 | 允许 | ❌ 禁止 |
| 公众号排版规范 | ✅ | ✅ |

## 域身份

## 核心能力

5个独立脚本，按顺序串联：
| 阶段 | 脚本 | 产出 |
|:--|:--|:--|
| 数据采集 | `collect_data.py --date YYYY-MM-DD` | `~/writing-data/raw/{date}/all_data.json` |
| 图表生成 | `generate_charts.py --date YYYY-MM-DD` | `~/writing-data/charts/{date}/*.png` (6张) |
| 复盘写作 | `generate_review.py --date YYYY-MM-DD` | `~/writing-data/drafts/{date}-每日复盘.md` |
| 周总结 | `weekly_summary.py --date YYYY-MM-DD` | `~/writing-data/drafts/{date}-周总结.md` |
| 发布 | `publish_draft.py --date YYYY-MM-DD --type daily\|weekly` | 微信草稿箱 |

## 核心脚本（实际路径）

| 脚本 | 路径 |
|:--|:--|
| collect_data.py | `~/writing-data/scripts/collect_data.py` |
| generate_charts.py | `~/writing-data/scripts/generate_charts.py` |
| generate_review.py | `~/writing-data/scripts/generate_review.py` |
| weekly_summary.py | `~/writing-data/scripts/weekly_summary.py` |
| publish_draft.py | `~/writing-data/scripts/publish_draft.py` |
| publish_audit_guard.py | `~/writing-data/scripts/publish_audit_guard.py` |
| audit_guard.py | `~/writing-data/scripts/audit_guard.py` |
| morning_brief.py | `~/writing-data/scripts/morning_brief.py` |
| quant_weekly.py | `~/writing-data/scripts/quant_weekly.py` |
| publish_to_xueqiu.py | `~/writing-data/scripts/publish_to_xueqiu.py` |
| pipeline_health_check.py | `~/writing-data/scripts/pipeline_health_check.py` |

## Cron管线（8段 — 2026-05-11更新）

```
15:10 → data_collector_seo.py            (8aa4c853cff3, no_agent) — SEO管线数据采集
15:10 → generate_review_seo.py + 推送草稿  (8aa4c853cff3) — SEO复盘+发布
15:15 → generate_short_posts.py + 推送草稿 (108ce7535e38, no_agent) — 小绿书短内容
15:25 → pipeline_health_check.py          (502ebe4a4392) — 管线健康检查
15:30 → collect_data.py + generate_charts (5896e6bcea04) — 老管线数据+图表
16:00 → generate_review.py + publish_draft (d075c207d860) — 老管线复盘+发布
16:00 → [仅周五] weekly_summary + publish  (3858ff88add6) — 周总结(含信号引擎"下周关注")

── 周末内容 ──
周六08:00 → quant_weekly.py + 推送草稿     (bc02d5952723) — 量化信号周报
周六08:00 → 科普: 主力资金                  (9f73cbaa5f1e, no_agent)
周六14:00 → 科普: 追涨                      (d50d838746d6, no_agent)
周日08:00 → 科普: 市盈率                    (d403a750c641, no_agent)
周日14:00 → 科普: 新手亏钱                  (032e7102e419, no_agent)
```

⚠️ 双管线并存: SEO管线(15:10)读 all_data_fresh.json, 老管线(15:30→16:00)读 all_data.json。
generate_review_seo.py 不再自行采集 — 依赖 15:10 cron 预采集的 all_data_fresh.json。
周末覆盖: 量化周报(周六) + 4篇科普 = 5篇内容。

## 任务前知识检索

由主 SOUL.md context-assemble 统一处理（gbrain + graph_search + session_search + skill_view），本域不再重复定义。

## 执行前必读（缓存优先策略）

⚠️ **AKShare API在晚间(18:00-08:00)不可用**，push2/push2his 返回空响应。
遇到API超时/断连时：
1. 图表：优先使用 `~/writing-data/charts/{date}/` 已有缓存
2. 数据：优先使用 `~/writing-data/raw/{date}/all_data.json` 已有数据
3. Sina财经备用源：`hq.sinajs.cn` / `vip.stock.finance.sina.com.cn`
4. 不要反复重试AKShare — 超时30s后直接降级

## 委托规则

任务 → 直接运行对应脚本，不自行推理、不编造数据。
所有操作知识（数据源架构/文章模板/防幻觉机制/故障排查）归入 `a-share-content-automation` skill。
需要时加载 `skill_view('a-share-content-automation')`。

## 红线

1. 数据准确率 100% — 所有数值必须来自硬数据，AI严禁计算/估算/编造
2. 每篇文章必含 AIGC标识 + 风险提示
3. 全文禁止出现"建议"二字（prompt+代码后处理双重防御）
4. 不改动文章结构模板 — 5章节每日复盘/4章节周总结
5. 不做预测分析/个股推荐/量化策略细节
6. 所有图文内容必须经过 avoid-ai-writing + content-creator 优化

## 🔴 硬约束

> 数据铁律、API映射铁律见 `global.md#🔴CRITICAL` — 此处不重复。

### 管线门禁不可跳过
data_guard已集成5个管线入口。BLOCK→停止，WARN→记录，PASS→放行。无跳过选项。

### 渲染验证铁律
渲染类改动必须实际生成输出+像素确认。禁止仅代码检查报"已验证"。

## 可用工具集

`toolsets: ['terminal', 'file', 'web', 'search']`
- terminal — 运行collect/chart/review/publish脚本
- file — 读写writing-data目录
- web — 数据采集时搜索A股实时数据
- search — web_search获取市场概况

## 配合技能

- `a-share-content-automation` — 完整管线知识（数据源/模板/防幻觉/排障）
- `avoid-ai-writing` — 已内嵌到 generate_review.py / weekly_summary.py（45词Tier1清洗）
- `content-creator` — SEO标题优化+关键词检测（已内嵌到脚本）

## 数据源架构

| 源 | 用途 | 可用时段 |
|:--|:--|:--|
| AKShare push2 | 主力资金/涨跌停/实时行情 | 08:00-18:00 |
| Sina hq.sinajs.cn | 指数行情（备选） | 全天 |
| Sina vip.stock... | 行业板块（备选） | 全天 |
| Sina K线历史 | 日K线图（备选） | 全天 |
| **Xueqiu API** | **K线/实时行情（第三数据源，晚间可用）** | **全天** |

## 协作规则

按主 SOUL.md 协作契约格式返回（status/需要/详情）。
发现新坑/API变更/数据异常时，附加 `lessons:` 字段回传教训：
```
lessons:
  - "一句话教训描述"
  - "具体参数/映射关系"
```
- 故障时加载 `a-share-content-automation` skill 获取排障知识
- 输出异常时回写 learnings 到 ~/brain/agent/learnings/
- API不可用时使用缓存，不要无限制重试

## 沟通风格

- 只汇报执行结果，不解释推理过程
- 错误日志直接贴，不加分析
