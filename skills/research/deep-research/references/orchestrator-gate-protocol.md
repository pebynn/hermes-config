# 研究任务强制协议 — Orchestrator Gate

部署于主 SOUL.md 的研究任务硬门禁（2026-05-01）。

## 触发词

研究 | 分析 | 调研 | 策略设计 | 方案设计

任一命中 → 禁止 web_search→直接给结论

## 协议步骤

1. **先查 wiki** — `mcp_llm_wiki_wiki_search` 查已有积累
2. **加载技能** — `skill_view(name='deep-research')` 获取 9 透镜
3. **派发研究** — delegate_task 给对应域（research-domain 或 finance-domain），传完整协议 + 四文件要求
4. **收验输出** — 总指挥创建 `~/research-skill-graph/projects/[项目名]/` 目录，确认四个文件齐全
5. **汇报** — 汇总 executive-summary + 标注 open-questions

## 成本规则

研究任务不设成本限制。禁止因省 token 缩水透镜数量或搜索深度。

## 输出检查

- [ ] wiki_search 已查
- [ ] 9 透镜全跑
- [ ] 四文件齐全（executive-summary / deep-dive / key-players / open-questions）
- [ ] `knowledge/concepts.md` + `data-points.md` 已更新

## 禁止模式

web_search 两下 → 口头结论 → 完事 = 违规

## 首用例

2026-05-01：stock-trading-theory-research（缠论/量价/经典指标）和 quant-system-design（四层量化系统），两个项目验证了完整协议。
