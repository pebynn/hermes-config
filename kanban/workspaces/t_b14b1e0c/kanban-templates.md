# Kanban Collaboration Templates
# code-domain + reviewer 自治审查修复闭环

## 任务创建流程

### Phase 1: 触发 → 审查任务
触发条件: PR 标记 'auto-review' 标签

kanban_create:
  title: "Review PR #{pr_number}"
  assignee: "reviewer"
  body: |
    ## 审查任务
    - PR: {pr_url}
    - Branch: {branch} → {base_branch}
    - 触发标签: auto-review
    - 迭代轮次: {iteration}

    ## 审查标准
    按优先级分类：安全(P0) > 性能(P1) > 风格(P2) > 逻辑(P3)
    详细标准见 review-criteria.json

    ## 产出要求
    1. 读取 PR diff
    2. 逐文件检查，按 criteria 分类 findings
    3. 将结果写入 ~/.hermes/bus/review-to-code/{pr_number}-{iteration}.json
    4. 在任务 metadata 中记录 findings 统计

    ## 强制规则
    - 安全类(P0) findings 的 requires_human 必须为 true
    - 涉及资金改动的 requires_human 必须为 true
    - findings 总数 > 20 时，block 等人工分流

---

### Phase 2: 审查完成 → 修复任务
触发条件: reviewer 审查任务完成，approved=false

kanban_create:
  title: "Fix PR #{pr_number} — {finding_count} findings (iter {iteration})"
  assignee: "code-domain"
  parents: ["{review_task_id}"]
  body: |
    ## 修复任务
    - PR: {pr_url}
    - Branch: {branch}
    - 迭代轮次: {iteration}
    - 数据总线: ~/.hermes/bus/review-to-code/{pr_number}-{iteration}.json

    ## 修复规则
    1. 读取数据总线中的 findings
    2. 按优先级顺序修复: P0 → P1 → P2 → P3
    3. 每个 finding 生成独立 commit
    4. P0(安全) 修复必须附带测试用例
    5. auto_fixable=false 的 finding 标记 [NEEDS-REVIEW]，跳过修复
    6. 修复完成后 push 到 PR branch

    ## 产出
    - 修复后的代码 (已 push)
    - metadata 中记录: findings_fixed, findings_skipped, commits

---

### Phase 3: 修复完成 → 验证任务
触发条件: code-domain 修复任务完成

kanban_create:
  title: "Verify PR #{pr_number} — iteration {iteration}"
  assignee: "reviewer"
  parents: ["{fix_task_id}"]
  body: |
    ## 验证任务
    - PR: {pr_url}
    - Branch: {branch}
    - 迭代轮次: {iteration}
    - 前次 findings 摘要: {previous_findings_summary}

    ## 验证标准
    1. 前次所有 findings 是否已修复
    2. 修复是否引入新问题 (全量重审)
    3. P0 修复是否有测试覆盖
    4. [NEEDS-REVIEW] 标记的 finding 是否被正确跳过

    ## 决策输出
    - approved=true: 所有问题已修复，无新问题
    - approved=false: 仍有问题，附带新 findings

    ## 迭代控制
    - 当前迭代: {iteration}
    - 最大迭代: 3
    - iteration >= 3 时: kanban_block("PR #{pr_number} 达到最大迭代次数 3，需要人工介入")

---

## 完整任务链路

```
t_review_1 (reviewer) ──→ t_fix_1 (code-domain) ──→ t_verify_1 (reviewer)
                                                        │
                                                    approved=false?
                                                        │
                                                        ↓
                                              t_fix_2 (code-domain) ──→ t_verify_2 (reviewer)
                                                                          │
                                                                      approved=false?
                                                                          │
                                                                          ↓
                                                                t_fix_3 (code-domain) ──→ t_verify_3 (reviewer)
                                                                                                │
                                                                                            still false?
                                                                                                │
                                                                                                ↓
                                                                                        kanban_block → 人工
```

## Metadata 传递格式

### reviewer 审查完成时
```json
{
  "pr_number": 123,
  "iteration": 1,
  "findings_count": {"P0": 2, "P1": 1, "P2": 3, "P3": 1},
  "approved": false,
  "review_task_id": "t_xxxx"
}
```

### code-domain 修复完成时
```json
{
  "pr_number": 123,
  "iteration": 1,
  "findings_fixed": 5,
  "findings_skipped": 2,
  "commits": ["abc1234", "def5678"],
  "review_task_id": "t_xxxx"
}
```

### reviewer 验证完成时
```json
{
  "pr_number": 123,
  "iteration": 1,
  "approved": true,
  "findings_fixed": 5,
  "new_findings": 0,
  "total_iterations": 1
}
```
