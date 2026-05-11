#!/usr/bin/env python3
"""post_kanban_complete.py — D层代码强制回收 (从worker结果提取lessons)
在 kanban_complete 后自动执行：解析[LESSONS]块 → 写入lessons文件 → 升级检查
用法：
  python3 post_kanban_complete.py --domain <domain> --result <result_text>
  python3 post_kanban_complete.py --task-id <t_xxx>  (从kanban.db自动提取)
  cat result.txt | python3 post_kanban_complete.py --domain <domain>
退出码0=成功
"""

import sys
import os
import re
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
LESSONS_DIR = HERMES_HOME / "lessons"
KANBAN_DB = HERMES_HOME / "kanban.db"

DOMAIN_LESSONS_MAP = {
    "code-domain": "code-domain.md",
    "code": "code-domain.md",
    "ops-domain": "ops-domain.md",
    "ops": "ops-domain.md",
    "finance-domain": "finance-domain.md",
    "finance": "finance-domain.md",
    "research-domain": "research-domain.md",
    "research": "research-domain.md",
    "writer": "writing-domain.md",
    "reviewer": "writing-domain.md",
    "ec-sourcing": "ec-domain.md",
    "ec-listing": "ec-domain.md",
    "ec-fulfillment": "ec-domain.md",
    "ec": "ec-domain.md",
}

def parse_lessons(result_text: str) -> list[dict]:
    """解析result中的[LESSONS]块"""
    if not result_text or '[LESSONS]' not in result_text:
        return []
    
    lessons = []
    # 提取[LESSONS]到下一个[标记或文本结束
    pattern = r'\[LESSONS\](.*?)(?=\n\[|\Z)'
    matches = re.findall(pattern, result_text, re.DOTALL)
    
    for block in matches:
        # 解析每条lesson
        # 格式: - level: 🔴/🟠/🟡  domain: <域>  content: <内容>  context: <场景>
        lesson_pattern = r'-\s*level:\s*(🔴|🟠|🟡|CRITICAL|HIGH|WARNING)\s*\n?\s*domain:\s*(\S+)\s*\n?\s*content:\s*(.+?)(?:\n\s*context:\s*(.+?))?(?=\n-|\n\n|$)'
        for m in re.finditer(lesson_pattern, block, re.DOTALL):
            level_raw = m.group(1).strip()
            level_map = {'🔴': '🔴 CRITICAL', 'CRITICAL': '🔴 CRITICAL', 
                        '🟠': '🟠 HIGH', 'HIGH': '🟠 HIGH',
                        '🟡': '🟡 INFO', 'WARNING': '🟡 INFO'}
            level = level_map.get(level_raw, f'🟡 {level_raw}')
            
            lessons.append({
                'level': level,
                'domain': m.group(2).strip(),
                'content': m.group(3).strip(),
                'context': (m.group(4) or '').strip(),
                'timestamp': datetime.now().isoformat()
            })
    
    return lessons

def lesson_exists(filepath: Path, content: str) -> int:
    """检查相似lesson是否已存在，返回出现次数"""
    if not filepath.exists():
        return 0
    
    text = filepath.read_text(encoding='utf-8')
    # 模糊匹配：前30字符
    key = content[:30].lower()
    count = text.lower().count(key[:20])
    return count

def append_lesson(filepath: Path, lesson: dict) -> bool:
    """追加lesson到文件"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    if not filepath.exists():
        filepath.write_text(f"# {filepath.stem} Lessons\n\n", encoding='utf-8')
    
    existing_count = lesson_exists(filepath, lesson['content'])
    
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(f"\n### {lesson['content'][:80]}\n")
        f.write(f"- **级别**: {lesson['level']}\n")
        f.write(f"- **域**: {lesson['domain']}\n")
        if lesson['context']:
            f.write(f"- **场景**: {lesson['context']}\n")
        f.write(f"- **发现时间**: {lesson['timestamp'][:19]}\n")
        f.write(f"- **出现次数**: {existing_count + 1}\n")
    
    return existing_count + 1 >= 2  # 返回是否需要升级

def get_summary_from_db(task_id: str) -> tuple[str, str]:
    """从kanban.db获取任务的summary和profile(domain)"""
    conn = sqlite3.connect(str(KANBAN_DB))
    cur = conn.execute(
        "SELECT r.summary, r.profile FROM task_runs r "
        "WHERE r.task_id=? AND r.outcome='completed' "
        "ORDER BY r.ended_at DESC LIMIT 1",
        (task_id,))
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        return row[0], row[1] or ""
    return "", ""

def main():
    parser = argparse.ArgumentParser(description="D层强制回收 — kanban_complete后置")
    parser.add_argument("--domain", help="Worker域名")
    parser.add_argument("--task-id", help="从kanban.db读取指定task的summary")
    parser.add_argument("--result", help="kanban_complete的result文本")
    parser.add_argument("--result-file", help="result文件路径")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    args = parser.parse_args()

    result_text = args.result
    domain = args.domain or ""
    
    # task-id模式：从db自动提取
    if args.task_id and not result_text:
        summary, profile = get_summary_from_db(args.task_id)
        if summary:
            result_text = summary
            domain = domain or profile
            print(f"[D层] 从task_runs提取: task={args.task_id} profile={profile} len={len(summary)}", file=sys.stderr)
        else:
            print(f"[D层] 未找到task={args.task_id}的已完成run", file=sys.stderr)
    
    if not result_text and args.result_file:
        result_text = Path(args.result_file).read_text(encoding='utf-8')
    if not result_text:
        result_text = sys.stdin.read().strip()

    if not result_text:
        print("[D层] 无输入", file=sys.stderr)
        sys.exit(0)

    lessons = parse_lessons(result_text)
    
    # 写入对应域文件
    written = []
    promoted = []
    
    for lesson in lessons:
        domain = lesson.get('domain', args.domain)
        lesson_file_name = DOMAIN_LESSONS_MAP.get(domain)
        if not lesson_file_name:
            # 模糊匹配
            for key, val in DOMAIN_LESSONS_MAP.items():
                if key in domain or domain in key:
                    lesson_file_name = val
                    break
            if not lesson_file_name:
                lesson_file_name = f"{domain}.md"
        
        filepath = LESSONS_DIR / lesson_file_name
        needs_promotion = append_lesson(filepath, lesson)
        written.append({
            'file': str(filepath),
            'content': lesson['content'][:60],
            'level': lesson['level']
        })
        
        if needs_promotion:
            promoted.append(lesson['content'][:80])
            # 标记为🔴CRITICAL
            content = filepath.read_text(encoding='utf-8')
            if '🔴 CRITICAL' not in content.split(f"### {lesson['content'][:80]}")[0][-200:]:
                # 把这条移到CRITICAL区
                pass  # 简化处理：不改动原有结构，只标记
    
    if args.json:
        print(json.dumps({
            "lessons_found": len(lessons),
            "written": len(written),
            "promoted": len(promoted),
            "details": written,
            "promotions": promoted
        }, ensure_ascii=False))
    else:
        if lessons:
            print(f"[D层回收] 发现{len(lessons)}条教训, 写入{len(written)}条", file=sys.stderr)
            for w in written:
                print(f"  → {w['file']}: {w['content']}", file=sys.stderr)
            if promoted:
                print(f"⚠️  升级告警: {len(promoted)}条教训需要升级为🔴CRITICAL", file=sys.stderr)
                for p in promoted:
                    print(f"  🔴 {p}", file=sys.stderr)
        else:
            print("[D层回收] 未发现[LESSONS]块", file=sys.stderr)

    sys.exit(0)

if __name__ == "__main__":
    main()
