# Pattern Generalization — 跨域教训联动的"举一反三"机制

## 问题

每次会话重启后，我是**孤立推理**的——当前上下文决定当前行为，不自动关联过往经验。lessons 按域加载限制了跨域模式识别：writing-domain 的教训不会出现在 quant-domain 任务中，即使逻辑相同。

## 现有基础设施诊断

| 系统 | 存储什么 | 怎么加载 | 跨域? | 可搜索? |
|:--|:--|:--|:--|:--|
| lessons/*.md | 域级教训（自由文本） | lesson_inject(domain) + global | 否（仅当前域） | 否 |
| graphify (275节点) | 文档索引 | graph_search(query) | 是 | 是（但无概念节点） |
| memory (target='user') | 用户偏好（扁平, 4K上限） | 每次会话自动注入 | 是 | 否 |
| memory (target='memory') | 环境事实 | 每次会话自动注入 | 是 | 否 |

三个系统各自为政。lessons 有含金量但无法被图检索。graph 有连接性但只有文件级节点（无概念节点）。user profile 有用户偏好但 4K 满了且扁平。

## 改造目标：三层联动

```
用户下发任务
  → user.md 加载 → "用户期望什么风格"
  → lesson_inject(domain) → "本域踩过什么坑"
  → graph_search(domain + task_keywords) → "其他域有没有同类教训"
  → 三条合并注入 context
```

## 需要做的改动

### 1. user.md 从 memory 迁移到文件系统

当前：memory target='user' 存 28 条/3981 字符，4K 上限，扁平不可搜。
改后：`~/.hermes/profiles/user.md`，结构化章节，无上限，graphify 可索引。

影响：
- freed 4K memory → 存 lessons 交叉引用索引
- 启动协议加一步 read_file user.md
- graphify 加索引路径
- memory tool 的 target='user' 不再使用

### 2. lessons 结构化升级

当前：自由文本，lesson_inject 按文件名（域）匹配。
改后：每条教训加 trigger_keywords 索引。

这样 graph_search("架构思路") 或 graph_search("方法论") 能命中，不受域限制。

### 3. context-assemble 加跨域搜索步骤

当前 delegate 前 pipeline：
[1] prompt-optimizer → [1.5] lesson_inject(domain) → [2] context-assemble → [3] delegate

改后：
[1] prompt-optimizer
→ [1.5] lesson_inject(domain) + user.md
→ [1.6] graph_search(domain + task_keywords) → 跨域教训
→ [2] context-assemble (包含三条)
→ [3] delegate

## 实施优先级

| 改动 | 工作量 | 效果 | 优先级 |
|:--|:--|:--|:--|
| lessons 加 trigger_keywords | 低（改 lesson_inject 写入格式） | 中（graph 可匹配） | P1 |
| user.md 迁移 | 中（建文件+写同步脚本） | 高（+4K memory + 可搜索） | P1 |
| context-assemble 加跨域搜索 | 低（加 graph_search 调用） | 高（跨域教训自动注入） | P1 |
| 启动协议读 user.md | 低（SOUL.md +1 步） | 中（每次会话加载用户偏好） | P1 |

## 限制

"举一反三"的核心瓶颈不在知识存储而在模式识别——lessons/graph/user.md 提供的是候选经验，但新场景和哪个旧模式匹配的识别能力取决于模型本身。三条数据源交叉命中能提高匹配概率，但不能保证 100% 自动匹配。
