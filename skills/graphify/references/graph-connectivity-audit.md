# 图谱连接性审计方法

用于诊断知识图谱的跨域关联健康度。输出 P0-P2 分级修复建议。

## 四步审计法

### Step 1: 规模基准
```
graph_stats → 取 total_nodes / total_edges / node_types
```
预期: edges > 2× nodes（健康比例），concept 类型 ≥ 5（概念节点是跨域桥的原料）

### Step 2: 域节点发现
```
graph_search("{domain} domain") × 6（code/ops/research/finance/writing/ec）
```
确认每个域都有文档节点存在。记录节点 ID（如 `.hermes::hermes_writing-domain`）。

### Step 3: 跨域路径测试（核心步骤）
```
graph_find_path(source=域A节点, target=域B节点) × 15（6域两两组合）
```
- 有路径 → ✅ 该域对有知识关联
- No path → ❌ 该域对孤立，标记为 P0 断裂
- 预期至少 finance↔writing 应有路径（A股数据处理共享）

### Step 4: 概念→域连接验证
```
graph_search("数据铁律") → 找到概念节点
graph_find_path(source=概念节点, target=域节点) → 测试概念是否连接到目标域
```
- 概念在 graph_search 能找到但 find_path 到域失败 → 命名空间隔离（参见 graphify SKILL.md §命名空间隔离）

## 常见断裂模式

| 断裂类型 | graph_search | graph_find_path | 根因 |
|:---------|:-----------|:---------------|:-----|
| 域节点孤岛 | 找到所有域节点 | 跨域全"No path" | 域文档间无连接边 |
| 命名空间隔离 | brain:: 和 .hermes:: 各有概念 | 跨命名空间"No path" | 双次爬取未合并 |
| 管道断裂 | 找到管道节点 | 仅有自引用边 | 管道定义存在但未连接数据流 |
| 教训缺失 | graph_search("lesson") 返回0 | N/A | lesson_graph_bridge 失效 |

## 修复优先级矩阵

| 优先级 | 条件 | 修复 |
|:------|:-----|:-----|
| P0 | 域对零路径或命名空间隔离 | 手动添加 `equivalent_to`/`shares_rule_with` 边到 graph.json |
| P1 | 管道节点仅自引用 | 连接管道节点到域节点 |
| P2 | 教训不进图谱 | 修复 lesson_graph_bridge.py 的 GRAPHIFY_BIN 路径 |

## 示例：本次审计(2026-05-10)发现
- brain:: 命名空间: brain_writing_domain 有22条连接边（健康）
- .hermes:: 命名空间: hermes_writing-domain 仅有1条自引用边（孤岛）
- 6域间 find_path 全部返回 "No path"（P0）
- lesson_graph_bridge.py GRAPHIFY_BIN=None（P0）
- pipeline-bus 仅自引用（P1）
- 教训注入管道(lesson_inject.py)正常但纯文本不入图
