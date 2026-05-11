# Memory Consolidation Playbook

> 当 memory 使用率 >85% 时的操作手册。memory-curator cron (2698791c5f60) 每天 03:00 自动执行。

## 判断阈值

| 使用率 | 动作 |
|:--|:--|
| <75% | 无操作 |
| 75-85% | 轻度合并（合并相关条目） |
| 85-95% | 主动精简（删除过时 + 压缩冗余） |
| >95% | 紧急清理（仅保留前10条 + 关键教训） |

## 清理优先级

### 第一优先：删除已完成/已过时的

逐个判断：这条信息现在还有用吗？

删除示例（2026-05-08 实测）：
- `sessions/ auto_prune 2026-05-06 发现并修复` → auto_prune 已正常工作，不需要记住修复过程
- `skill-security-auditor已MCP化` → 信息已合并到 MCP工具链 条目

### 第二优先：合并相关条目

找属于同一主题的条目，合并为一条。

合并示例：
- `MCP新增2个` + `skill-security-auditor已MCP化` → `MCP工具链` (节省 ~300 chars)
- `DSPy self-evolution` 相关已死信息 → 直接删除

### 第三优先：压缩冗余细节

- 去掉文件数量（"13个脚本" → "scripts集"）
- 去掉具体版本号（"uv 0.11.8, ruff 0.15.12" → "uv+ruff+pre-commit"）
- 去掉数据库行数（"5066行" → 删除）
- 去掉命令输出/密码（"pwd='***'" → 删除）

## 保留原则

以下类型的信息即使占空间也保留：
1. **用户偏好/纠正** — 如 "先给方案再开干"
2. **API 映射铁律** — 如 "parts[1]=今开, parts[2]=昨收"
3. **当前系统的配置事实** — 如 模型路由、cron ID 列表
4. **硬约束/红线** — 如 "禁自行计算涨跌幅"

## 工具命令

```bash
# 替换条目（最常用）
memory(action='replace', target='memory', 
       old_text='唯一子串', content='精简版')

# 删除过时条目
memory(action='remove', target='memory', 
       old_text='唯一子串')

# 新增（仅放关键新信息）
memory(action='add', target='memory', content='...')
```

## 效果记录

2026-05-10 手动压缩: 99%(5,962) → 43%(2,586), 31条→13条, 节省3,376 chars (-56%)
  方法: 分类→去重(与global.md/domain-lessons交叉比对)→合并(5条公众号→1条)→下沉细节→lessons
  关键: Sina API映射(global.md已完整)、Playwright(ops-domain已完整) 从memory删除
  保留: 5条铁律、模型路由、死路、API黑窗、writing-domain全貌(合并版)

2026-05-08 手动清理: 98%(5,938) → 77%(4,650), 26条→24条, 节省1,288 chars

## 分层注入策略（2026-05-10 新增）

当 memory 压缩到 <50% 后，不应继续压缩内容本身，而应改变**注入方式**：

| 层级 | 内容 | 注入时机 | 大小目标 |
|:--|:--|:--|:--|
| Tier 1 核心 | 5条铁律 + API映射 + 死路 | 每轮必注 | ~2,000 chars |
| Tier 2 域激活 | writing/SEO规则 / finance/量化规则 | 对应域活跃时 | ~2,000 chars |
| Tier 3 搜索 | 历史细节 / 一次性修复 | session_search按需 | 不限 |

改造方式：修改 SOUL.md 启动协议，从"读全部文件"改为"读索引+按域注入"。
详见 context-compression-protocol 策略F。
