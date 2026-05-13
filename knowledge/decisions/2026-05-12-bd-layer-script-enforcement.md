# D002: B+D 层脚本强制执行 — 纯文本约束不可靠

**日期**: 2026-05-12
**级别**: 🔴 架构级决策
**决策者**: 用户反馈 → Hermes 执行

## 决策

将 B (lesson injection before kanban_create) 和 D (lesson feedback collection after kanban_complete) 从 SOUL.md 纯文本约束升级为**脚本强制执行**：

- `pre_kanban_create.py` — B层注入：读lessons/ → 提取🔴CRITICAL → 注入body+成本预估
- `post_kanban_complete.py` — D层回收：解析[LESSONS] → 写文件 → ≥2次升级告警
- `audit_bd_layer.py` — 每日审计cron → B/D注入率<阈值 → QQ Bot告警

## 理由

1. **纯文本约束不可靠**: SOUL.md 中的 "L1/L2 后不加问号" 被 agent 反复违反
2. **行为层面不可靠**: agent "听到"规则但在推理中忽略
3. **用户明确拒绝文本方案**: "很明显，加文本约束并不能让你严格执行"
4. **脚本化 = 硬约束**: 代码级拦截 → 无法跳过

## 代价

- 每次 kanban_create 额外调用 1 个 Python 脚本（~100ms）
- 需维护 lessons/ 目录同步

## 后续

- 2026-05-11: SOUL.md 写入 B+D 协议文本 → 当日发生 2 次 L2 违规
- 2026-05-12: 脚本化方案上线 → audit cron `e07573d46f12`
- 2026-05-12: 验证 cron `3619b0cd1e81` 确认协议遵守
- 待解决: Gateway hooks 进一步强制执行 L1/L2/L3 决策矩阵
