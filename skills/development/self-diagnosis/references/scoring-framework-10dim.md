# 10-Dimension System Scoring Framework

Developed during 2026-05-04 comprehensive system audit. Used when user asks for self-assessment or "给自己打分".

## Dimensions

| # | Dimension | Weight | What to check |
|:--|:----------|:------:|:--------------|
| 1 | 架构合规性 | 15% | orchestrator开关正确性, spawn_depth合理性, 工具分层完整性, local profile残留 |
| 2 | 文件组织 | 10% | 根目录数据文件=0, PDD/quant/文档目录规范性, .hermes体积 |
| 3 | 配置完整性 | 10% | 域config存在, delegation配置, orchestrator误开, delivery errors |
| 4 | 技能生态 | 10% | 技能总数, issues占比, 交叉引用有效性, 空目录 |
| 5 | 知识图谱 | 5% | MCP graph可用性, wiki同步, GBrain索引完整性 |
| 6 | 定时任务 | 10% | cron status覆盖率, delivery errors, gateway健康 |
| 7 | 域能力成熟度 | 15% | 逐域评分(ec/code/finance/ops/research), 工作流完整性 |
| 8 | 成本效率 | 10% | 模型选择(flash vs pro), tokscale可用性, circuit-guard |
| 9 | 自进化基础 | 10% | self-evolution目录完整性, archive_learning活跃度, reactive-skillify |
| 10 | 记忆系统 | 5% | Memory使用率, 条目数, 用户画像完整度 |

## Scoring Formula

```
综合 = Σ(维度分 × 权重)
```

## 2026-05-04 Baseline

综合: 70.3/100

| Dimension | Score |
|:----------|:-----:|
| 架构合规性 | 75 |
| 文件组织 | 82 |
| 配置完整性 | 70 |
| 技能生态 | 65 |
| 知识图谱 | 60 |
| 定时任务 | 80 |
| 域能力成熟度 | 72 |
| 成本效率 | 65 |
| 自进化基础 | 55 |
| 记忆系统 | 70 |

Top 3 硬伤: self-evolution空转, Memory 94%, research-domain orchestrator误开.

## Trend Tracking (GStack health)

每次评分后追加到 `~/.hermes/health/history.jsonl`（每行一个JSON对象）：

```json
{"date": "2026-05-15", "composite": 70.3, "dimensions": {"架构合规性": 75, ...}}
```

**趋势对比规则：**
1. 读取最近2条历史记录
2. 对比综合分：±5以内=稳定，+5以上=改善，-5以下=退化
3. 逐维度对比：单维度下降>15分 → 独立告警
4. **连续2次退化** → QQ Bot告警（hermes-notify）
5. 仅保留最近20条（自动剪枝）

**输出增强**（在评分矩阵后追加）：
```
趋势: ↑改善 / →稳定 / ↓退化
较上次: +X.X / -X.X
退化维度: <维度名>(-X分) [仅当有退化时显示]
```
