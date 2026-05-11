#!/usr/bin/env python3
"""域成熟度量化评分 — 每周评估各域自主能力"""
import json
from datetime import datetime
from pathlib import Path

HOME = Path.home()
PROFILES = HOME / '.hermes' / 'profiles'
LESSONS = HOME / '.hermes' / 'lessons'

# 评分维度权重
WEIGHTS = {
    'soul_size': 0.10,       # SOUL.md 行数
    'scripts': 0.25,         # 自动化脚本数
    'crons': 0.25,           # 定时任务数
    'lessons': 0.15,         # 教训密度（越多越成熟）
    'tools': 0.15,           # 可用工具/API
    'autonomy': 0.10,        # 自主修复能力
}

def score_domain(domain):
    profile = PROFILES / domain
    if not profile.exists():
        return None

    scores = {}

    # 1. SOUL 大小
    soul = profile / 'SOUL.md'
    soul_lines = len(soul.read_text().split('\n')) if soul.exists() else 0
    scores['soul_size'] = min(soul_lines / 200, 1.0)

    # 2. 脚本数
    scripts_dir = profile / 'skills'
    script_count = 0
    if scripts_dir.exists():
        for py_file in scripts_dir.rglob('*.py'):
            if py_file.stat().st_size > 100:
                script_count += 1
    scores['scripts'] = min(script_count / 5, 1.0)

    # 3. Cron 数（基于 pipeline.yaml）
    pipeline = HOME / '.hermes' / 'agenda' / 'pipeline.yaml'
    cron_count = 0
    if pipeline.exists():
        content = pipeline.read_text()
        for keyword in [domain.replace('-domain', ''), 'writing', 'quant', 'ec', 'finance']:
            cron_count += content.count(f'cron:')
    cron_count = max(cron_count, 1)
    scores['crons'] = min(cron_count / 5, 1.0)

    # 4. 教训密度
    lesson_file = LESSONS / f'{domain}.md'
    lesson_lines = 0
    if lesson_file.exists():
        content = lesson_file.read_text()
        lesson_lines = content.count('## 🔴') * 3 + content.count('## 🟠') * 2 + content.count('## 🟡')
    scores['lessons'] = min(lesson_lines / 15, 1.0)

    # 5. 工具/API 丰富度
    tools_keywords = ['api', 'curl', 'playwright', 'browser', 'mysql', 'akshare', 'pandas']
    tool_hits = sum(1 for kw in tools_keywords if kw in soul.read_text().lower()) if soul.exists() else 0
    scores['tools'] = min(tool_hits / 5, 1.0)

    # 6. 自主性（基于 SOUL 内容）
    autonomy_keywords = ['自主', '自动', '主动', '审计', '修复', '检测', '验证']
    autonomy_hits = sum(1 for kw in autonomy_keywords if kw in soul.read_text()) if soul.exists() else 0
    scores['autonomy'] = min(autonomy_hits / 5, 1.0)

    # 加权总分
    total = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    return {
        'domain': domain,
        'score': round(total * 100),
        'details': {k: round(v * 100) for k, v in scores.items()},
        'soul_lines': soul_lines,
        'scripts': script_count,
        'crons': cron_count,
    }


if __name__ == '__main__':
    domains = [d.name for d in PROFILES.iterdir() if d.is_dir() and (d / 'SOUL.md').exists()]
    results = []
    for d in sorted(domains):
        r = score_domain(d)
        if r:
            results.append(r)

    results.sort(key=lambda x: x['score'], reverse=True)

    print(f"# 域成熟度报告 — {datetime.now().strftime('%Y-%m-%d')}")
    print()
    for r in results:
        bar = '█' * (r['score'] // 10) + '░' * (10 - r['score'] // 10)
        print(f"## {r['domain']}: {r['score']}% {bar}")
        print(f"  SOUL: {r['soul_lines']}行 | 脚本: {r['scripts']} | Cron: {r['crons']}")
        det = r['details']
        print(f"  规模:{det['soul_size']}% 脚本:{det['scripts']}% 任务:{det['crons']}% 教训:{det['lessons']}% 工具:{det['tools']}% 自主:{det['autonomy']}%")
        print()

    # 输出升级建议
    print("## 🔧 升级建议")
    for r in results:
        if r['score'] < 40:
            print(f"  {r['domain']}: 需重点升级（SOUL+脚本+自主性全面薄弱）")
        elif r['score'] < 60:
            weak = [k for k, v in r['details'].items() if v < 40]
            print(f"  {r['domain']}: 短板 — {', '.join(weak)}")

    # 保存
    report_file = HOME / '.hermes' / 'agenda' / 'domain_maturity.md'
    report_file.parent.mkdir(exist_ok=True)
    import sys
    sys.stdout.flush()
