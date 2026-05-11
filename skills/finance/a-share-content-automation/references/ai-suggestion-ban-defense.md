# AI "建议"违禁词防御纵深

**问题**：weekly_summary.py 和 generate_review.py 的 prompt 模板中已明确约束"全文严禁出现'建议'二字"，但 DeepSeek 仍会输出含"建议"的内容（如"操作建议""投资建议""仓位管理建议"等）。

**根因**：LLM 对 prompt 末尾约束的遵从度不足，尤其是中文写作模型对"禁止词"指令的敏感性低于"应该怎么做"指令。

**适用范围**：`weekly_summary.py` + `generate_review.py` 均已集成（2026-05-05）。

## 防御纵深设计

### Layer 1: Prompt 硬性约束（提前到数据段之前）

将"建议"禁令从 prompt 末尾的约束区提升到 **数据段之前**，用"硬性约束（违反则全文无效）"的措辞，并提供明确的替代词映射表：

```
## ⚠️ 硬性约束（违反则全文无效）

1. **全文严禁出现"建议"二字**。包括但不限于："操作建议""投资建议""仓位建议"...
   用词替代：建议→思路/要点/方向，操作建议→关注方向，投资建议→投资参考...
2. **第4节标题必须是"关注方向"**，不是"操作建议""下周策略""操作思路"等任何变体。
3. 以上两条零容忍。违反一条即视为不合格。
```

关键设计：
- 放在数据段**之前**而非写作要求中（AI 先读到约束再读到数据）
- "零容忍""即视为不合格"的措辞强化严重性
- 提供完整的替代词映射表，减少 AI "不知道该用什么替代"的困惑
- generate_review.py 也用此模式，但将"第4节"改为通用的"文章章节标题"

### Layer 2: 后处理硬拦截（代码层兜底）

即使 prompt 正确，AI 仍可能输出违禁词。在 content 生成后、保存前加入后处理（`weekly_summary.py` 和 `generate_review.py` 均实现）：

```python
# 1. 检测违禁复合短语
for phrase in ["操作建议", "投资建议", "仓位建议", "止盈止损建议",
               "配置建议", "持仓建议", "仓位管理建议"]:
    count = content.count(phrase)

# 2. 逐项替换（复合短语优先）
content = content.replace("仓位管理建议", "仓位管理思路")
content = content.replace("操作建议", "关注方向")
content = content.replace("投资建议", "投资参考")
# ... 等

# 3. 常见句式替换
content = content.replace("建议关注", "可关注")
content = content.replace("建议止损", "可考虑止损")
content = content.replace("建议总仓位", "总仓位可考虑")
# ... 等

# 4. 兜底：残留裸"建议"直接删除
residual = content.count("建议")
if residual > 0:
    content = content.replace("建议", "")

# 5. 验证第4节标题（仅 weekly_summary.py）
h4_match = re.search(r'(?:^|\n)##?\s*4\.?\s*[【\[]?\s*(.+?)\s*[】\]]?\s*\n', content)
if "建议" in h4_title:
    content = content.replace(h4_title, "关注方向")
```

### 替换词映射表

| 违禁短语 | 替换为 | 优先级 |
|:---------|:-------|:------|
| 仓位管理建议 | 仓位管理思路 | 复合短语优先匹配 |
| 操作建议 | 关注方向 | — |
| 投资建议 | 投资参考 | — |
| 仓位建议 | 仓位管理 | — |
| 止盈止损建议 | 止盈止损参考 | — |
| 配置建议 | 配置方向 | — |
| 持仓建议 | 持仓思路 | — |
| 建议关注 | 可关注 | 句式级替换 |
| 建议止损 | 可考虑止损 | — |
| 建议总仓位 | 总仓位可考虑 | — |
| 建议XXX | (删除) | 兜底裸词删除 |

## 验证方法

```bash
# 周总结
python3 weekly_summary.py --date YYYY-MM-DD 2>&1 | grep "违禁词"

# 每日复盘
python3 generate_review.py --date YYYY-MM-DD 2>&1 | grep "违禁词"

# 期望输出：
# ⚠️ AI违禁词检测: 操作建议(1次), 投资建议(2次)    ← 如果有违规
# ✅ 违禁词已清除，最终'建议'出现次数: 0               ← 确认清除

# 或（如果没有违规）：
# （无违禁词检测行 — 说明AI直接遵从了约束）
```

## 相关脚本变更（2026-05-05）

- `weekly_summary.py`: prompt 加固 + 后处理 + 第4节标题校验
- `generate_review.py`: prompt 加固 + 后处理 + AIGC标识中的"投资建议"修→"投资参考"
- `publish_draft.py`: 元数据段剥离加固（含 `---` 分隔符），`--validate` 模式
