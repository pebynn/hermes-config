# 2026-05-10 上下文瘦身成果

完整记录见 `soul-maintenance-audit` skill `references/optimization-results-2026-05-10.md`

## 关键数据

| 指标 | 之前 | 之后 | 节省 |
|:--|:--|:--|:--|
| MEMORY | 5,962 chars | 2,586 chars | -57% |
| USER PROFILE | 3,874 chars | 1,780 chars | -54% |
| Skills (active) | 171 | 144 | -18 removed |
| Profiles (6 domains) | 37,010 chars | 21,304 chars | -42% |
| 启动协议读取 | ~35KB | ~5KB | -86% |
| **每会话固定开销** | **~130KB** | **~85KB** | **-35%** |

## 配置变更

- memory_char_limit: 6000→4000
- user_char_limit: 4000→2000
- compression.threshold: 0.5→0.7
- compression.target_ratio: 0.2→0.3
