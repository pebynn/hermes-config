# audit_guard 统一架构 (2026-05-07)

## 背景

`audit_guard.py` 原有两个独立版本：
- **A版** (review-writer/scripts/, 823行)：合规检测 + 数据准确性 + AI味检测 (3维)
- **B版** (publisher/scripts/, 701行)：合规检测 + 数据准确性 + 格式质量 (3维)

两版规则有重叠但不完全相同，A版缺少格式质量检测（章节完整性/字数/图表引用/Tier1密度），B版缺少AI编造检测和三连排比检测。

## 统一后架构

```
review-writer/scripts/audit_guard.py  ← 统一核心模块 (~540行)
  ├── 1. 合规检测 (A+B并集): 个股推荐+违禁词+违规承诺+AIGC标识+风险提示
  ├── 2. 数据准确性 (A+B并集): 交叉验证+AI编造检测
  ├── 3. AI味检测 (A+B并集): 残留词+Em dash+粗体+三连排比+Tier1密度
  ├── 4. 格式质量 (B版): 章节完整性+字数+图表引用
  ├── audit_draft() — 主入口，返回Dict
  └── CLI: --date/--file/--type/--json/--quiet

publisher/scripts/audit_guard.py    ← 轻量wrapper (~130行)
  └── import audit_draft from 统一核心
      + --auto-publish 开关逻辑
      + 彩色输出 (保持B版风格)
```

## 规则合并清单

| 规则 | 来源 | 维度 |
|------|------|------|
| STOCK_ADVICE_TRIGGERS (16词) | A版 | 合规(BLOCK) |
| 个股推荐模式正则 (6条) | B版 | 合规(BLOCK) |
| ILLEGAL_PROMISE_TRIGGERS (17词) | A版 | 合规(BLOCK) |
| 夸大收益正则 (5条) | B版 | 合规(BLOCK) |
| "建议"复合模式 (4条) + 裸词检测 | B版 | 合规(BLOCK) |
| AIGC标识 | A+B | 合规(BLOCK) |
| 风险提示 | B版 | 合规(WARN) |
| 交叉验证 (4类数字) | A版 | 数据(WARN) |
| AI编造检测 | A版 | 数据(WARN) |
| AI_VOCAB_SCAN_WORDS (106词) | A版 | AI味(WARN) |
| Em dash / 粗体 / 三连排比 | A+B | AI味(WARN) |
| Tier1词密度 | B版 | AI味(WARN) |
| 章节完整性 + 字数 + 图表引用 | B版 | 格式(WARN) |

## 导入方式

```python
# 从 publisher wrapper 看导入链
import sys
from pathlib import Path

_REVIEW_WRITER_SCRIPTS = (
    Path.home() / ".hermes" / "profiles" / "writing-domain"
    / "skills" / "a-share-review-writer" / "scripts"
)
sys.path.insert(0, str(_REVIEW_WRITER_SCRIPTS))
from audit_guard import audit_draft

result = audit_draft(date_str="2026-05-07", draft_type="daily")
# result["risk_level"] → PASS/WARN/BLOCK
# result["exit_code"] → 0/1/2
```

## 退出码行为

- A版 CLI: --date/--file/--json/--quiet 保持，退出码 0/1/2
- B版 wrapper: --date/--type/--auto-publish 保持，audit通过(exit=0)时自动调用 publish_draft.py
