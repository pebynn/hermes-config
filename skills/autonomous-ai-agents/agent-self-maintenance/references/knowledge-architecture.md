# 知识体系架构 (2026-05-09 重构)

## 问题: 6套知识系统各自为政

| 系统 | 查 | 写 | 原来用在哪 |
|:--|:--|:--|:--|
| memory | 自动注入 | memory() | 每次会话 |
| lessons | lesson_inject | lesson_inject add | delegate 前 |
| graphify | graph_search | cron 03:00 扫 brain | 手动搜 |
| wiki | wiki_search | 研究时写 | 手动搜 |
| gbrain | 不直接查 | cron 同步 | 只能通过 graphify |
| user profile | memory user 自动注入 | memory action=add | 每次会话 |

## 方案: 三合一，lesions 为主存储

```
纠正/观察发生
  │
  ├──→ lessons/{domain}.md (主存储, 全文)
  │     含: 教训(🔴🟠🟡) + 用户偏好(👤) + 死路(🗑️)
  │
  ├──→ memory user (热缓存, 5条铁律)
  │     仅存最核心的铁律级别规则
  │     每次会话自动注入，100%覆盖
  │
  └──→ ~/brain/lessons/{domain}-{title}.md (graphify 桥)
        graphify 03:00 cron 自动索引
        跨域搜索用
```

## 三层的职责

| 层 | 容量 | 覆盖 | 更新频率 |
|:--|:--|:--|:--|
| memory user (5条铁律) | ~500字符 | 每条消息 | 低（只有铁律变化时才改） |
| lessons/{domain}.md | 无上限 | delegate 前+会话启动 | 中（每次纠正） |
| graphify/brain | 无上限 | 跨域搜索 | 低（每日索引） |

## 写入入口

```
纠正/错误 → lesson_inject add --severity CRITICAL
  → lessons/*.md (全文)
  → post-hook 提示同步 memory (只有 CRITICAL 级别)

观察/偏好 → profile_observe.py
  → lessons/global.md 👤 章节
  → 如果是铁律级偏好 → 手动补充 memory user

环境事实 → memory target=memory (不变量)
  → API 凭证、路径、配置等不会变的信息
```

## 启动加载链路

```
每条消息   : memory user 5条铁律 (自动注入)
每会话启动 : read_file lessons/global.md (完整画像)
每次 delegate 前: lesson_inject(domain) (本域教训)
跨域搜索   : graph_search(task_keywords) (命中其他域教训)
```

## 一致性保证

- lessons 是唯一写入点，memory user 是 lessons 的 CRITICAL 子集投影
- 不存在"lessons 说A，memory 说B"的情况
- 过期处理：lessons 带时间戳，90天无更新的 lessons 标记陈旧
