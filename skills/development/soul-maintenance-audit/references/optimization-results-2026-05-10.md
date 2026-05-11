# 2026-05-10 系统优化全记录

## 执行摘要

一轮完整系统优化循环，覆盖记忆/上下文/启动/技能/管道/配置 6 个层面。

## 记忆系统

| 项目 | 之前 | 之后 | 压缩率 |
|:--|:--|:--|:--|
| MEMORY.md | 5,962 chars / 31条 | 2,586 chars / 13条 | -57% |
| USER.md | 3,874 chars / 29条 | 1,780 chars / 8条 | -54% |
| memory_char_limit | 6,000 | 4,000 | 对齐上限 |
| user_char_limit | 4,000 | 2,000 | 对齐上限 |

压缩方法: 四步法 (分类分级→去重→合并→下沉)
- 去重: Sina API映射/Playwright等 → 已有 lessons 中完整版本，memory 只留速查
- 合并: 5条公众号相关 → 1条 "writing-domain全貌"
- 下沉: browser_publish.py 14步流程 → writing-domain.md

## 上下文瘦身

| 项目 | 节省 |
|:--|:--|
| 删除18个无用技能 | ~12KB |
| 启动协议瘦身 (5步→3步, 跳过pipelines.json) | ~30KB |
| Profile SOUL.md 压缩 (ec 89%↓, code 89%↓) | ~16KB |
| 上下文压缩阈值调优 (0.5→0.7, 0.2→0.3) | 减少过早压缩 |

每轮对话固定开销: ~130KB → ~85KB (-35%)

## 任务处理

- 管道检查点系统: pipeline_checkpoint.py (save/resume/clear)
- 三级故障恢复: 重试→重规划→分解细化 (写入SOUL.md)
- 3条completed pipeline → 归档

## 配置调优

| 参数 | 原值 | 新值 | 原因 |
|:--|:--|:--|:--|
| memory_char_limit | 6000 | 4000 | 官方推荐2200，用户设4000 |
| user_char_limit | 4000 | 2000 | 官方推荐1375，用户设2000 |
| compression.threshold | 0.5 | 0.7 | 避免过早触发压缩 |
| compression.target_ratio | 0.2 | 0.3 | 保留更多推理上下文 |

## 教训

1. **批量操作先dry-run**: 归档技能时误移107个(目标18)，2分钟内回滚
2. **Hindsight安装失败**: Python构建兼容性问题(setuptools use_2to3)，跳过外部后端
3. **Profile知识分层**: 领域深度知识应在skills中(按需加载)，profile只留角色+规则