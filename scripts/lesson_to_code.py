#!/usr/bin/env python3
"""
教训→代码闭环 — 从 lessons/ 中提取可行动化建议，自动生成 SOUL.md/skill 修改。
配合 error-learner cron (575103045eb1) 使用。

用法: python3 lesson_to_code.py --domain <domain> [--dry-run]
在 error-learner 产出新 lesson 后自动触发。
"""
import os
import sys
import re
import json
from datetime import datetime
from pathlib import Path

LESSONS_DIR = os.path.expanduser("~/.hermes/lessons")
SOUL_MD = os.path.expanduser("~/.hermes/SOUL.md")
SKILLS_DIR = os.path.expanduser("~/.hermes/skills")

def parse_lessons(domain_file):
    """解析教训文件，提取可行动化建议"""
    if not os.path.exists(domain_file):
        return []
    
    with open(domain_file) as f:
        content = f.read()
    
    actions = []
    
    # 查找 "纠正次数: 2+" 或 "纠正次数: N" 的教训
    pattern = r'(?:###|##)\s+([^\n]+)\n((?:(?!###|##).+\n)+)'
    for match in re.finditer(pattern, content):
        title = match.group(1).strip()
        body = match.group(2).strip()
        
        # 提取纠正次数
        corr_match = re.search(r'纠正次数[：:]\s*(\d+)', body)
        corr_count = int(corr_match.group(1)) if corr_match else 0
        
        # 只处理纠正2次以上的教训（需要代码固化）
        if corr_count >= 2:
            # 检查是否已有对应的脚本/规则
            has_script = bool(re.search(r'scripts?/[a-z_]+\.(py|sh)', body, re.IGNORECASE))
            has_rule = bool(re.search(r'SOUL\.md|规则化|已固化', body))
            
            if not has_script and not has_rule:
                actions.append({
                    'title': title,
                    'corrections': corr_count,
                    'body': body[:300],
                    'domain': os.path.basename(domain_file).replace('.md', ''),
                    'action': '需要代码固化（≥2次纠正但无对应脚本/规则）'
                })
    
    return actions

def suggest_fix(action):
    """根据教训内容建议修复方式"""
    title = action['title'].lower()
    body = action['body'].lower()
    
    if 'api' in title or '映射' in title or '字段' in title:
        return "建议: 创建字段映射配置文件 + 脚本化验证"
    elif '路径' in title or '目录' in title:
        return "建议: 在 SOUL.md 中硬编码路径 + 启动检查脚本"
    elif 'cron' in title or '调度' in title:
        return "建议: 创建 cron 冲突预检脚本"
    elif '验证' in title or '检查' in title:
        return "建议: 创建自动化验证脚本并集成到管线"
    elif '模型' in title or 'model' in title:
        return "建议: 在 config.yaml 中配置 circuit-breaker"
    else:
        return "建议: 评估是否可脚本化；不可则写入 SOUL.md 硬约束"

def main():
    import argparse
    parser = argparse.ArgumentParser(description='教训→代码闭环')
    parser.add_argument('--domain', help='指定域（不指定则扫描所有）')
    parser.add_argument('--dry-run', action='store_true', help='仅分析不执行')
    parser.add_argument('--json', action='store_true', help='JSON输出')
    args = parser.parse_args()
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'total_lessons': 0,
        'actionable': [],
        'suggestions': []
    }
    
    # 扫描教训文件
    if args.domain:
        files = [os.path.join(LESSONS_DIR, f'{args.domain}.md')]
    else:
        files = sorted(Path(LESSONS_DIR).glob('*.md'))
        files = [str(f) for f in files if not f.name.startswith('_') and f.name != 'global.md']
    
    for f in files:
        if not os.path.exists(f):
            continue
        actions = parse_lessons(f)
        results['total_lessons'] += len(actions)
        for a in actions:
            fix = suggest_fix(a)
            entry = {**a, 'suggested_fix': fix}
            results['actionable'].append(entry)
    
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    
    print(f"=== 教训→代码闭环分析 ===")
    print(f"扫描域数: {len(files)}")
    print(f"需固化的教训: {len(results['actionable'])}")
    print()
    
    if not results['actionable']:
        print("✅ 所有教训已固化，无待处理项。")
        return 0
    
    for a in results['actionable']:
        print(f"🔴 [{a['domain']}] {a['title']}")
        print(f"   纠正次数: {a['corrections']}")
        print(f"   {a['suggested_fix']}")
        print()
    
    print(f"总结: {len(results['actionable'])}个教训需要代码固化。")
    if args.dry_run:
        print("(dry-run模式，未执行修改)")
    
    return len(results['actionable'])

if __name__ == '__main__':
    sys.exit(main())
