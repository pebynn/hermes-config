---
title: "模板 — 归档条目格式说明"
type: learning
created: "YYYY-MM-DD HH:MM:SS +0800"
source_files:
  - "path/to/file1.py"
  - "path/to/file2.sh"
tags:
  - "category"
  - "sub-category"
---

## 摘要

用 ≤200 字总结 delegate_task 的关键发现。

## 源文件

file1.py, file2.sh

## 记录时间

YYYY-MM-DD HH:MM:SS +0800

---

## 自动归档

```
python3 scripts/archive_learning.py \
    --topic "你的主题" \
    --summary "你的摘要" \
    --source "文件1,文件2" \
    --tags "标签1,标签2"
```

## 生成规则

- 文件名: `YYYY-MM-DD-topic-slug.md`
- slug: 小写 → 空格变连字符 → 去特殊字符
- 不覆盖已有文件
- summary ≤200 字
- 自动创建 ~/brain/agent/learnings/ 目录
