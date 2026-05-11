# Code-Review 自治修复闭环设计文档

## 1. 概述

建立 code-domain (实现者) + reviewer (审查者) 的自治代码审查修复闭环。参考 Planner-Generator-Evaluator 模式，实现：发现问题 → 自动修复 → 验证 → 合入/回退。

## 2. 角色定义

| 角色 | Profile | 职责 |
|------|---------|------|
| **reviewer** | reviewer | 读取 PR diff，生成结构化审查反馈 |
| **code-domain** | code-domain | 消费审查反馈，逐项修复代码 |
| **verifier** | reviewer | 对修复后的代码重新审查，决定合入/回退 |

## 3. 流程设计

```
[PR 事件] → 触发脚本 → kanban_create(review task)
                                    ↓
                          reviewer 审查 PR diff
                          生成结构化反馈 (findings[])
                                    ↓
                          kanban_create(fix task, parent=review)
                                    ↓
                          code-domain 消费反馈
                          逐项修复 → 写回 PR branch
                                    ↓
                          kanban_create(verify task, parent=fix)
                                    ↓
                          reviewer 重新审查
                          ├── 通过 → 合入建议
                          └── 不通过 → 回退到 fix (迭代计数+1)
                                    ↓
                          迭代计数 >= 3 → kanban_block (人工介入)
```

## 4. Kanban 任务模板

### 4.1 审查任务 (reviewer)

```json
{
  "title": "Review PR #{pr_number}",
  "assignee": "reviewer",
  "body": "## 审查任务\n- PR: {pr_url}\n- Branch: {branch}\n- 触发标签: auto-review\n- 迭代轮次: {iteration}\n\n## 审查标准\n按优先级分类：安全 > 性能 > 风格 > 逻辑\n\n## 产出\n结构化 JSON findings，格式见 review-schema.json",
  "parents": []
}
```

### 4.2 修复任务 (code-domain)

```json
{
  "title": "Fix PR #{pr_number} — {finding_count} findings",
  "assignee": "code-domain",
  "body": "## 修复任务\n- PR: {pr_url}\n- Branch: {branch}\n- 迭代轮次: {iteration}\n\n## 审查反馈\n{findings_json}\n\n## 修复规则\n1. 按优先级顺序修复 (安全 > 性能 > 风格 > 逻辑)\n2. 每个 finding 生成独立 commit\n3. 安全类修复必须附带测试\n4. 不确定的修复标记为 [NEEDS-REVIEW]",
  "parents": ["{review_task_id}"]
}
```

### 4.3 验证任务 (reviewer)

```json
{
  "title": "Verify PR #{pr_number} — iteration {iteration}",
  "assignee": "reviewer",
  "body": "## 验证任务\n- PR: {pr_url}\n- Branch: {branch}\n- 迭代轮次: {iteration}\n- 前次 findings: {previous_findings_summary}\n\n## 验证标准\n1. 前次 findings 是否全部修复\n2. 修复是否引入新问题\n3. 安全类修复是否有测试覆盖\n\n## 决策\n- 全部通过 → metadata.approved = true\n- 存在问题 → metadata.approved = false, 添加新 findings",
  "parents": ["{fix_task_id}"]
}
```

## 5. 审查标准定义

### 5.1 问题分类与优先级

| 优先级 | 类别 | 权重 | 示例 |
|--------|------|------|------|
| P0 - Critical | 安全 (security) | 100 | SQL注入、XSS、硬编码密钥、不安全反序列化 |
| P1 - High | 性能 (performance) | 75 | N+1查询、内存泄漏、缺失索引、O(n²)可优化 |
| P2 - Medium | 风格 (style) | 50 | 命名不规范、缺少docstring、过长函数、重复代码 |
| P3 - Low | 逻辑 (logic) | 25 | 边界条件未处理、错误处理不完整、竞态条件 |

### 5.2 Finding 结构

```json
{
  "id": "F001",
  "severity": "P0",
  "category": "security",
  "file": "src/api/search.py",
  "line": 42,
  "title": "SQL Injection in search endpoint",
  "description": "User input directly concatenated into SQL query",
  "suggestion": "Use parameterized queries",
  "auto_fixable": true,
  "requires_human": false
}
```

### 5.3 强制规则

1. **安全类 (P0) 修复**：必须有 reviewer 最终确认 (`requires_human = true`)
2. **资金相关改动**：任何涉及支付/金额的修改，`requires_human = true`
3. **auto_fixable = false** 的 finding 不自动修复，标记 [NEEDS-REVIEW]
4. 单个 PR findings 超过 20 个，block 等人工分流

## 6. 迭代控制

```
iteration = 0: 初始审查
iteration = 1: 第1轮修复+验证
iteration = 2: 第2轮修复+验证
iteration = 3: 第3轮修复+验证
iteration >= 3: kanban_block("PR #{pr} 达到最大迭代次数 3，需要人工介入")
```

每轮迭代在 kanban 任务 metadata 中记录：
```json
{
  "iteration": 2,
  "findings_fixed": 5,
  "findings_remaining": 1,
  "new_findings": 0,
  "total_iterations": 3
}
```

## 7. 触发机制

### 7.1 GitHub PR Webhook (推荐)

- 监听 `pull_request` 事件，action = `opened | synchronize | labeled`
- 仅当 PR 被标记 `auto-review` 标签时触发
- 调用 `pr_auto_review.py` 创建审查任务

### 7.2 定时扫描 (备选)

- cron 定期扫描仓库中带 `auto-review` 标签的 open PR
- 检查 PR 的最新 commit 是否已被审查过
- 未审查的 PR 触发审查流程

## 8. 数据总线

审查反馈通过 kanban metadata 传递，格式：

```
~/.hermes/bus/review-to-code/{pr_number}-{iteration}.json
```

Schema:
```json
{
  "pr_number": 123,
  "pr_url": "https://github.com/org/repo/pull/123",
  "branch": "feature/new-api",
  "iteration": 1,
  "findings": [...],
  "summary": "3 P0, 2 P1, 5 P2 findings",
  "approved": false,
  "reviewer_task_id": "t_xxxx"
}
```

## 9. 不影响手动流程

- `auto-review` 标签是 opt-in 机制
- 未标记的 PR 不受影响
- 人工审查结果优先于自动审查
- 任何阶段人工介入可覆盖自动决策

## 10. 限制与风险

| 风险 | 缓解措施 |
|------|----------|
| 误报导致错误修复 | 安全/资金类必须人工确认 |
| 修复引入新 bug | 验证阶段全量重审 |
| 迭代不收敛 | 3轮上限 block 人工 |
| 大 PR 审查超时 | findings > 20 直接 block |
| GitHub API 限流 | 指数退避重试，最长间隔 5min |
