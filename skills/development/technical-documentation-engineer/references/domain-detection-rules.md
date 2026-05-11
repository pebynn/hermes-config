# Domain Detection Rules — task-clarify.py

`scripts/task-clarify.py` uses regex-based keyword matching to infer which Hermes
domain should handle a user request. This file documents the rules so they can
be maintained without reading the source.

## Priority Order (first match wins)

| Order | Domain | Keywords |
|:------|:-------|:---------|
| 1 | `finance` | 股票, 量化, 回测, 因子, 选股, A股, 估值, 投资, 基本面, 财报, k线/k圖, 行情, 交易, 持仓, 盈亏 |
| 2 | `ec` | 选品, 上架, 订单, 电商, pdd, 拼多多, 17网, 女装, 套装, 运营, listing, sourcing, fulfillment, 退货, 定价, 款式 |
| 3 | `research` | 研究, 分析, 调研, 报告, research, 竞品, 市场趋势, 深度, 挖一挖, 找找看 |
| 4 | `ops` | 部署, deploy, 安装, install, 配置, cron, 定时, 运维, docker, server, 后台, 监控 |
| 5 | `code` | 写, 改, 修, 代码, code, bug, git, commit, pr, python, 脚本, script, 重构, refactor, 测试, test, debug, fix, patch |

Default: `general`

## Negation Handling

Before matching, negated commands are stripped from the input:
```
不要改, 别改, 不改, 不要修, 别修, 不修, 不要动, 别动, 不动
```

This prevents "不要改参数" from matching the `code` domain via the "改" keyword.
The stripped text is used for domain inference only; the original text is used
for constraint extraction.

## Priority Inference

| Priority | Triggers |
|:---------|:---------|
| P0 | 紧急, urgent, 立刻, 马上, fix, 修复, bug, crash, 挂了 |
| P1 | 重要, 必须, 一定, 今天, immediate |
| P2 | everything else (default) |

## Constraint Extraction

| Pattern | Constraint |
|:--------|:-----------|
| 不要改/别改/不改... | `no-modify` |
| 只看/只查... | `read-only` |
| 仅分析 | `analysis-only` |

Constraints are passed to `delegate_task` context so sub-agents respect them.

## Edge Cases

### "做研究" vs "研究"
"做研究" and "研究一下" match the `research` keyword "研究". This is intentional —
both imply a research task. If the user says "研究一下这个bug" (investigate this bug),
the word "bug" appears in the `code` domain but "研究" appears in `research`.
Since `research` checks before `code` (order 3 vs 5), it would be classified as
`research`. To force `code`, use `--domain-hint code`.

### "帮我分析一下这个策略回测"
Contains both "分析" (research, order 3) and "回测" (finance, order 1).
Finance wins because it's checked first. This is correct — strategy backtest
analysis is a finance task, not a generic research task.

### "安装python脚本"
Contains "安装" (ops, order 4) and "脚本" (code, order 5).
Ops wins because it's checked first. This is correct — installing is an ops task,
even if the thing being installed is a script.
