# Graphify Cron 集成模式

## 概览

Graphify 跑完后不是终点。以下四种后处理模式将图谱发现闭环回知识库。

## 模式 1: see-also 反向链接回写

```bash
# 从 GRAPH_REPORT.md 提取 Surprising Connections
# 对每条跨文件的 INFERRED 边：
python3 -c "
import re
report = open('graphify-out/GRAPH_REPORT.md').read()
# 匹配行: `source` --relation--> `target` [INFERRED]
pattern = r'\`(.+?)\` --(.+?)--\> \`(.+?)\`\s+\[INFERRED\]'
for m in re.finditer(pattern, report):
    source = m.group(1)
    relation = m.group(2)
    target = m.group(3)
    print(f'{source}|{relation}|{target}')
" > /tmp/surprising.txt

# 对每对文件追加 see-also 区块
while IFS='|' read -r source rel target; do
    # 映射 node label → wiki file path（需根据实际映射表）
    # source_page = normalize(source)
    # target_page = normalize(target)
    
    # 追加到 source 页面
    # if ! grep -q "## See Also" "$source_page"; then
    #     echo -e "\n## See Also" >> "$source_page"
    # fi
    # echo "- [[$target_page]] — $rel [INFERRED]" >> "$source_page"
done < /tmp/surprising.txt
```

**规则：**
- 只处理 INFERRED 边（EXTRACTED 的已在原文中明确）
- 检查 `## See Also` 是否已有相同链接
- 两端页面都加交叉链接

## 模式 2: memory-summary 注入

每周 cron 最后一步写 `memory-summary-latest.md`：

```markdown
---
date: YYYY-MM-DD
type: graph-summary
---
# 知识图谱周报

## 统计
- 节点: N / 边: N / 社区: N
- 本周新增: N 节点 / N 边
- 提取: X% EXTRACTED / X% INFERRED

## God Nodes (前5)
1. {label} — {degree} 边
...

## 跨社区桥
- {bridge} — 中介中心性 {score}，连接 C{id} → C{id}

## 本周意外发现
- {source} --{relation}--> {target} [{confidence}]
```

主 SOUL.md 规则：会话启动时 `terminal cat` 此文件，注入摘要到后续任务理解。

## 模式 3: 退化告警

每次 cron 对比上次和本次统计。触发条件写入 ALERT.md：

| 条件 | 级别 |
|------|------|
| 节点数下降 ≥10% | critical |
| 边数下降 ≥10% | critical |
| God Node 前5任意出榜 | warning |
| 新增社区（孤立风险） | warning |
| 无退化 | 删除 ALERT.md |

会话启动时检测 ALERT.md 存在 → 主动向用户汇报。

## 模式 4: learnings 反馈扫描

cron 扫描 `~/brain/agent/learnings/` 本周新增条目。关键词匹配到 skill/profile 引用 → 追加到 GRAPH_REPORT.md：

```
## Learnings Feedback
本周 learnings 归档发现：
- {文件名}: {主题} — 建议更新 {skill名} 的 {章节}
```

## 完整 cron 时间线

```
每周一：
  03:00  wiki-graphify-weekly        ~/brain/ 图谱 + 回写 + 告警 + 反馈
  05:00  hermes-profiles-graphify    ~/.hermes/profiles/ 域能力图
  06:00  hermes-skills-graphify      ~/.hermes/skills/ 技能依赖图
```
