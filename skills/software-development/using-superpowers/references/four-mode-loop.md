# 四模式操作回路 — 详细执行手册

> 2026-05-10 会话反思产物。文本约束对我没用，这4个模式是操作习惯，不是文本规则。

## 模式A：决策前强制回路

适用于：每次需要判断、分析、评估的操作。

```
mcp_graphify.graph_search(query=任务关键词)
  → 发现知识图谱中65K节点的关联
mcp_sequential_thinking.sequentialthinking()
  → 分步推理 ≥3步
  → 分支探索 → 假设验证 → 收敛
memory铁律自检
  → 5条逐句对照
执行
```

**触发词**：分析、评估、判断、预测、找出原因、为什么、审查

**反例**：用户问"审查所有发现过又没有修复的问题" → 直接search_files+列出问题。  
**正例**：graph_search查关联 → sequential-thinking分步推理 → 判断哪些L1直接修哪些L3请示 → 执行+汇报。

## 模式B：delegate后验证回路

适用于：每次 delegate_task 返回后。

```
delegate_task 返回 summary
  → stat 检查产出文件是否存在
  → py_compile 验证.py语法
  → diff 对比修改内容
  → 提取新发现 → lesson_inject add
  → 汇报修改验证结果
```

**反例**：子代理说"已完成5个文件修改" → 直接接受summary。  
**正例**：stat验证5个文件存在 → py_compile语法检查 → grep确认关键词出现在文件中 → 汇报"已验证5文件"。

## 模式C：会话启动自主扫描

适用于：每次新会话启动时。

```
读 daily.md + task_tracker.json
  → 扫描 lessons/*.md 中"待修复/TODO/FIXME"
  → 扫描 task_tracker P1滞留项
  → 扫描 cron last_status=error
  → 扫描 成本异常
  → L1直接修 → L2修后简报 → L3列出
```

**反例**：启动时只读daily.md汇报三件套，等用户问"有什么问题"。  
**正例**：主动发现session-miner死循环、cost-tracker归零、finance待修复项，全部处理完再汇报。

## 模式D：输出前铁律自检

适用于：每次输出给用户前。

```
1. 数据来自API原始值？没自行计算涨跌幅/成交额/涨跌家数？
2. L1直接做了没问？L2修完简报？L3才问？
3. 有"可以吗/怎么样/需要我/要推进吗"？→删掉直接做
4. 同类问题全局排查了？没单点打补丁？
5. ≥3阶段走pipeline了？完成→验证→立即下一阶段？
```

违反任何一条 → 改写输出，不发送原始版本。
