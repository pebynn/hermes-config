#!/usr/bin/env python3
"""
会话知识归档 — delegate_task 关键发现写入 wiki learnings 目录。

用法:
  python3 scripts/archive_learning.py \
      --topic "修复了Parquet时区偏移bug" \
      --summary "pandas to_parquet默认UTC导致+8偏移，改用tz='Asia/Shanghai'修复" \
      --source "fix_tz_bug.py,quant_pipeline.py" \
      --tags "bugfix,quant,parquet,timezone"

输出: ~/brain/agent/learnings/YYYY-MM-DD-topic-slug.md
返回 0 = 成功, 1 = 失败
"""

import argparse, os, re, sys
from datetime import datetime, timezone


def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r'[^a-z0-9\u4e00-\u9fff\s-]', '', s)
    s = re.sub(r'\s+', '-', s.strip())
    s = re.sub(r'-+', '-', s)
    return s.strip('-') or 'untitled'


def archive_learning(topic: str, summary: str, source: list[str],
                     tags: list[str]) -> str:
    now = datetime.now(timezone.utc).astimezone()
    created_at = now.strftime('%Y-%m-%d %H:%M:%S %z')

    base_dir = os.path.expanduser('~/brain/agent/learnings')
    os.makedirs(base_dir, exist_ok=True)

    date_str = now.strftime('%Y-%m-%d')
    topic_slug = slugify(topic)[:80].rstrip('-')
    filename = f'{date_str}-{topic_slug}.md'
    filepath = os.path.join(base_dir, filename)

    if os.path.exists(filepath):
        raise FileExistsError(f'文件已存在: {filepath}')

    source_yaml = '\n'.join(f'  - "{s}"' for s in source) if source else '  []'
    tags_yaml = '\n'.join(f'  - "{t}"' for t in tags) if tags else '  []'

    content = f"""---
title: "{topic}"
type: learning
created: {created_at}
source_files:
{source_yaml}
tags:
{tags_yaml}
---

## 摘要

{summary}

## 源文件

{', '.join(source) if source else '无'}

## 记录时间

{created_at}
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    os.chmod(filepath, 0o644)
    return filepath


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='归档 delegate_task 发现到 wiki learnings')
    p.add_argument('--topic', required=True)
    p.add_argument('--summary', required=True)
    p.add_argument('--source', default='', help='逗号分隔源文件')
    p.add_argument('--tags', default='', help='逗号分隔标签')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args(argv)

    if len(args.summary) > 200:
        print(f'错误: summary >200字 ({len(args.summary)})', file=sys.stderr)
        return 1

    source_list = [s.strip() for s in args.source.split(',') if s.strip()]
    tags_list = [t.strip() for t in args.tags.split(',') if t.strip()]

    try:
        if args.dry_run:
            print(f'[DRY RUN] 将归档到 ~/brain/agent/learnings/ ...')
            print(f'  topic:   {args.topic}')
            print(f'  summary: {args.summary}')
            print(f'  source:  {source_list}')
            print(f'  tags:    {tags_list}')
            return 0
        filepath = archive_learning(args.topic, args.summary, source_list, tags_list)
        print(f'归档成功: {filepath}')
        return 0
    except FileExistsError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f'归档失败: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
