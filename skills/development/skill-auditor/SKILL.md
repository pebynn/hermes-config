---
allowed-tools:
- read_file
- search_files
- terminal
- skills_list
- skill_view
- write_file
- patch
author: unknown
description: 技能生态完整性审计 — 检查所有安装技能的 frontmatter/交叉引用/前置依赖/脚本语法/目录健康度。安装后审计，非安全方向
execution: manual
name: skill-auditor
version: 1.0.0
when-to-use: '用户说：

  - "检查技能有没有问题"

  - "审计技能"

  - "技能健康检查"

  - "配合技能引用是不是对的"

  - "哪些技能装坏了"

  - After mass skill install/upgrade

  - Periodic maintenance (monthly)'
---

# 技能生态审计

## 审计维度

| # | 维度 | 检查项 | 严重程度 |
|:--|:-----|:-------|:--------|
| 1 | Frontmatter | 所有 SKILL.md 的 YAML frontmatter 是否完整、必填字段(name/description/version)是否存在 | P1 |
| 2 | Frontmatter | allowed-tools 引用的工具名是否有拼写错误 | P2 |
| 3 | 文件完整性 | linked_files 中引用的路径是否真实存在于磁盘 | P1 |
| 4 | 文件完整性 | SKILL.md 中引用的脚本/配置文件路径是否有效 | P2 |
| 5 | 交叉引用 | 域 SOUL.md 配合技能节引用的 skill 是否已安装 | P1 |
| 6 | 交叉引用 | skills_list 返回的技能名与磁盘 SKILL.md 数量是否一致 | P2 |
| 7 | 目录健康 | 空 skill 目录（无 SKILL.md） | P2 |
| 8 | 目录健康 | 同一 skill 出现在多个分类目录下的重复注册 | P3 |
| 9 | 前置依赖 | skill 声明的 required_commands 对应的命令是否可执行 | P2 |
| 10 | 前置依赖 | skill 声明的 required_environment_variables 对应的环境变量是否有值 | P2 |
| 11 | 前置依赖 | skill 声明的 missing_credential_files 是否指向真实存在的文件 | P3 |
| 12 | 脚本语法 | skill 目录下所有 .py 文件能否通过 ast.parse 编译 | P1 |
| 13 | 交叉引用 | related-skills 前字段引用的技能在 SKILL.md 正文中是否有对应引用（双向一致性） | P2 |
| 14 | 分类健康 | 分类目录数量是否合理 | P3 |

## 执行流程

### Phase 1: 采集基线

```bash
# 1. 技能总数 + 分类目录
find ~/.hermes/skills -name 'SKILL.md' | sort > /tmp/skill_all_paths.txt
ls -d ~/.hermes/skills/*/ | sort > /tmp/skill_categories.txt

# 2. 空目录
find ~/.hermes/skills -empty -type d > /tmp/skill_empty_dirs.txt

# 3. 分类下的 SKILL.md 分布
for cat in $(ls -d ~/.hermes/skills/*/); do
  count=$(find "$cat" -name 'SKILL.md' | wc -l)
  echo "$(basename $cat): $count"
done
```

### Phase 2: Frontmatter 审计

遍历每个 SKILL.md，检查：

1. **必填字段缺失** — 用 Python 解析 YAML frontmatter：
   - `name` 是否存在
   - `description` 是否存在
   - `version` 是否存在
   - `allowed-tools` 是否存在（可选但建议）

2. **allowed-tools 拼写校验** — 检查是否引用了不存在或不合理的工具名（如 `execute_command` 应为 `terminal`）

3. **linked_files 路径验证** — 如果 SKILL.md 中有 linked_files 声明，检查每个路径是否实际存在

### Phase 3: 交叉引用审计

1. **SOUL.md 配合技能** — 遍历 5 个域 SOUL.md：
   ```
   grep -A5 '配合技能' ~/.hermes/profiles/*/SOUL.md | grep '`' | sed 's/.*`\(.*\)`.*/\1/'
   ```
   提取所有被引用的 skill 名称 → 与 `skills_list` 的输出对比 → 标记缺失

3. **skills_list vs 磁盘** — `skills_list` 输出的技能名数量 vs 磁盘上 SKILL.md 数量。如果差异大，说明有技能未注册或重复注册

### Phase 3b: 交叉引用双向一致性审计（新增 P2 维度）

检查每个 SKILL.md 中 `related-skills` 字段与正文中的技能引用是否双向一致：

1. 提取 frontmatter `related-skills` 列表
2. 扫描 SKILL.md 正文，找出所有反引号包裹的 skill 名引用（如 `` `pdd-store-matrix` ``）
3. 比对：正文引用了某 skill，但 frontmatter `related-skills` 中没有 → 标记缺失
4. 推理：frontmatter `related-skills` 中列了某 skill，但正文没有对应引用 → 标记冗余（P3）
5. 跨技能联动检查：A 引用 B，B 的 related-skills 是否也引用了 A？


### Phase 4: 前置依赖检查（重编号）

对每个 SKILL.md，检查 readiness_status 相关字段：
- `required_commands` — 每个命令用 `which` 或 `command -v` 检查
- `required_environment_variables` — 用 `echo ${VAR:-}` 检查是否为空
- `missing_credential_files` — 检查指向的文件是否存在
- `missing_required_commands` — 汇总所有缺失的命令
- `missing_required_environment_variables` — 汇总所有缺失的环境变量

### Phase 5: 脚本语法检查

```bash
python3 -c "
import ast, os
errors = []
for root, dirs, files in os.walk(os.path.expanduser('~/.hermes/skills')):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                with open(path) as fh:
                    ast.parse(fh.read())
            except SyntaxError as e:
                errors.append(path)
for e in errors:
    print(e)
"
```

### Phase 6: 汇总报告

按 P1/P2/P3 三级输出：

```
## 技能生态审计报告

### P1 — 必须修
[N] 条 — 影响功能

### P2 — 建议修
[N] 条 — 潜在问题

### P3 — 可优化
[N] 条 — 整洁性

### 概览
| 指标 | 数值 |
|:----|:----:|
| 技能总数 | N |
| 分类目录 | N |
| 有问题技能 | N |
| 空目录 | N |
| 配合技能缺失引用 | N |
| 脚本语法错误 | N |
| 前置依赖缺失 | N |
```

## 自动修复

对于以下问题可自动修复（仅在用户确认后执行）：

| 问题 | 修复方式 |
|:-----|:---------|
| 空分类目录 | `find ~/.hermes/skills -empty -type d -delete` |
| 脚本语法错误 | 报告路径让 code-domain 修复 |
| missing_credential_files 指向不存在文件 | 在 skill 中更新路径或删除引用 |

## 已知常见问题

| 模式 | 原因 | 修复 |
|:-----|:-----|:-----|
| 社区skill安全block | 社区skill含exfiltration/traversal风险（如ai-seo被block: data exfiltration + path traversal） | 不force安装。改用内置能力替代（如writer SEO优化内置到SOUL.md），或搜索官方Hub的official source |
| skills_list 比磁盘少 | skill 目录在磁盘存在但未注册到 Hermes 内部索引 | 重启 Hermes 或手动注册 |
| 配合技能引用不存在的 skill | SOUL.md 更新但 skill 被删/改名未同步 | 更新 SOUL.md 引用或补装 |
| linked_files 指向已删除文件 | skill 文件重构后 linked_files 未更新 | 更新 SKILL.md 中的 linked_files 列表 |
| required_commands 缺失 | 系统重装/环境变更后命令不可用 | 重装对应工具或更新 skill |
| 空分类目录 | 删除最后一个 skill 后未清理目录 | 自动删除空目录 |
| related-skills 双向不一致 | 正文引用了某技能但 frontmatter 未添加；或 A 有 B 但 B 没有 A | 手动补全 frontmatter，跨技能联动添加 |
