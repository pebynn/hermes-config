# 记忆瘦身操作手册

当 MEMORY usage > 85% 或条目 > 25 时执行。

## 四步压缩法（2026-05-10 实战验证：31条→13条, -56%）

### 步骤 0: 诊断

```bash
wc -c ~/.hermes/memories/MEMORY.md  # 字符数
grep -c '§' ~/.hermes/memories/MEMORY.md  # 条目数
```

### 步骤 1: 分类分级

逐条标注严重度：
- 🔴 CRITICAL：API映射、死路、fallback、数据铁律 — 必须保留在memory
- 🟠 HIGH：cron/pipeline/域特定规则 — 可压缩为摘要
- 🟡 MEDIUM：历史细节、已完成的修复记录 — 可下沉到lessons

### 步骤 2: 去重检查（memory ↔ lessons）

扫描每条memory是否已在lessons中有更完整版本：

| 示例 | 处理 |
|:--|:--|
| Sina API字段映射(memory) vs global.md CRITICAL段 | memory删除，lessons保留 |
| Playwright安装流程(memory) vs ops-domain.md | memory删除，lessons保留 |
| 公众号发布流程(memory) vs writing-domain.md | memory删除，lessons保留 |

### 步骤 3: 合并同类

同主题多条 → 合并为一条：
- 5条公众号相关(SEO/排版/发布/草稿箱/配图) → 1条"writing-domain全貌"
- 多条用户偏好 → 1条"5条用户铁律"
- 多条效率规则 → 合并到铁律中

### 步骤 4: 下沉细节

| 保留在 memory | 迁移到 lessons |
|:--|:--|
| 每轮必查的铁律（数据准确性/API字段映射） | 详细实现步骤（browser_publish 14步流程） |
| 当前系统状态（模型路由/活跃cron/基建） | 历史教训上下文（为什么某方案被否决） |
| 死路标记（PDD API不可用） | 域级技术文档（data_guard架构设计） |
| 用户偏好（沟通风格/cost敏感） | 一次性修复记录（某次bug修复过程） |

### 步骤 5: 验证

```bash
for kw in "API铁律" "死路" "DeepSeek" "pipeline" "PDD" "QQ Bot"; do
  echo -n "$kw: "; grep -c "$kw" ~/.hermes/memories/MEMORY.md
done
# 每个关键词应 ≥1 且 ≤2
```

## 已验证的合并示例

| 合并前 | 合并后 |
|:--|:--|
| "速度优化: 多步机械→execute_code..." + "多次纠正分批操作..." | "效率铁律: 多步机械→execute_code; ≤3步→不走delegate; 无依赖→并行" |
| 5条公众号相关(SEO/排版/发布/草稿箱/配图) | "writing-domain全貌: 脚本统一~/writing-data, data_guard门禁, 公众号15:10推送..." |
| 10条用户偏好碎片 | "5条用户铁律" + "画像" + "沟通" 三条压缩 |

## 效果验证

```
# 目标：usage < 70%，条目 < 20（优化后标准）
```

## ⚠️ 批量操作陷阱（2026-05-10 教训）

执行批量 `mv`/`rm` 操作时必须三步法：
1. **先 dry-run** 列出所有将被操作的目标，确认数量匹配预期
2. **人工确认** 范围正确
3. **执行后立即验证** 结果数量

反例：18个目标技能 → 脚本范围错误 → 107个被误移 → 需紧急回滚。
