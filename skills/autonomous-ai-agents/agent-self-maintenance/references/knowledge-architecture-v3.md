# Knowledge Architecture v3 — 层域知识串联 (2026-05-10)

## Three Actions

### 1. 决策回路嵌入graph_search
SOUL.md启动协议: 分析类任务触发前强制 `graph_search(query)`→关联节点注入context。
enforce_delegate.py v2 自动检测"分析/评估/判断/预测"关键词→触发graph_search。

### 2. 知识总线 lesson_graph_bridge.py
lesson_inject写入新教训→自动触发graphify节点创建。
cross-domain-sync cron后运行graphify跨域边创建。
实现 graphify↔lessons↔profiles 三层互通。

### 3. 域profiles强制知识引用
每个profile/SOUL.md加: `📖 知识引用: global.md#🔴CRITICAL | lessons/{domain}.md | graphify:lesson:{domain}`
删除profiles中与global.md重复的规则副本。
writing-domain数据铁律+API映射→改为引用global.md。

## Knowledge Flow
```
新教训 → lesson_inject.py → global.md
    ↓ (自动触发)
lesson_graph_bridge.py → graphify节点
    ↓
cross-domain-sync(cron) → 跨域关联边
    ↓
下次分析任务 → graph_search → 注入context
```
