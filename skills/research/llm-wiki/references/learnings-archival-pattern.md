# 会话知识归档模式 (Session-to-Learnings Archival)

## 问题

delegate_task 执行完成后，有价值的关键发现散落在会话上下文中。下次会话或子代理无法复用这些结论，导致重复工作和知识流失。

## 方案

每次 delegate_task 成功后，通过 `scripts/archive_learning.py` 将关键发现写入 `~/brain/agent/learnings/YYYY-MM-DD-topic-slug.md`。

## 目录结构

```
~/brain/agent/
├── learnings/                    # 归档目录（本模式）
│   ├── 2026-05-03-时区修复.md
│   ├── 2026-05-03-知识归档初始化.md
│   └── template.md              # 格式模板
└── ...                           # 其他 wiki 内容
```

## 触发方式

**自动触发（主代理 SOUL.md 规则）：**
在 delegate_task 成功后，检查结果摘要 → 判断是否有可归档发现 → 调用脚本。

**手动触发：**
```
python3 scripts/archive_learning.py \
    --topic "..." --summary "..." --source "f1,f2" --tags "t1,t2"
```

## SOUL.md 规则建议

```yaml
# 在 SOUL.md 的 delegate_task 执行规则中添加：
after-skill-delegate-task-success:
  - 检查子代理返回结果中是否含"关键发现"标记
  - 如发现新知识/修复/结论 → 调用 archive_learning.py 归档
  - 在汇报末尾注明"📖 已归档到 learnings/"
```

## 集成管道

```
delegate_task 完成
    ↓
是否有可归档发现？
    ├── 否 → 跳过
    └── 是 → archive_learning.py
        ↓
写入 ~/brain/agent/learnings/<date>-<slug>.md
    ↓
gbrain search cron（每6小时）自动索引新文件
    ↓
后续会话可通过 gbrain/graphify 双路检索回溯
```

## 与 wiki 的关系

| 对比项 | wiki (entities/concepts/) | learnings/ |
|--------|---------------------------|------------|
| 粒度 | 结构化、可编辑的实体/概念页 | 按时间排列的发现归档 |
| 生命周期 | 持续维护、更新 | 创建后不变（append-only） |
| 格式共性 | YAML frontmatter + markdown | 同上 |
| 创造者 | 主动 ingest 或手动编辑 | auto-archive from delegate_task |
| 使用者 | 所有会话的 wiki query | 主代理做 research 时回溯 |
| 触发 | 用户发起或策划 | delegate_task 完成后自动触发 |

## 坑点

- **不要归档 trivial 信息** — 只归档可复用的发现（bug 修复、工作流、验证结论）
- **summary ≤200 字** — 脚本强制校验
- **不覆盖已有文件** — 同一 topicslug 不会覆盖，必须手动删除或换 topic
- **文件归属** — `learnings/` 不是 wiki 的一部分，是 wiki 的"新闻源"——新知识先出现于 learnings，后可能迁移到 wiki 实体/概念页
