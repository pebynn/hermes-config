#!/usr/bin/env python3
"""
lessons_to_graphify_sync.py — 夜间 lessons → graphify 知识图谱同步脚本

从 ~/.hermes/lessons/*.md 解析教训条目，通过直接操作 graph.json
添加 lesson 节点及与域节点的关联边。幂等（基于内容哈希去重）。

Usage:
  python3 lessons_to_graphify_sync.py              # 正常同步
  python3 lessons_to_graphify_sync.py --dry-run     # 预览
  python3 lessons_to_graphify_sync.py --graph PATH  # 指定graph路径
"""

import argparse, hashlib, json, os, re, sys
from pathlib import Path
from datetime import datetime

# ── 配置 ─────────────────────────────────────────────────────────────
# 使用硬编码绝对路径，因为 kanban 工作区会覆盖 $HOME
BASE = Path('/home/pebynn/.hermes')
DEFAULT_GRAPH = '/home/pebynn/brain/graphify-out/graph.json'
LESSONS_DIR = BASE / 'lessons'
# 跳过 _daily_audit_ 这类非领域 lesson 文件
SKIP_FILES = re.compile(r'^_')

SEVERITY_MAP = {
    '🔴': 'CRITICAL', 'CRITICAL': 'CRITICAL',
    '🟠': 'HIGH',     'HIGH': 'HIGH',
    '🟡': 'MEDIUM',   'MEDIUM': 'MEDIUM',
}

# 域名 → graph 中域节点 ID 映射
DOMAIN_NODE_MAP = {
    'ops-domain': 'ops_domain',
    'code-domain': 'code_domain',
    'ec-domain': 'ec_domain',
    'finance-domain': 'finance_domain',
    'research-domain': 'research_domain',
    'writing-domain': 'writing_domain',
    'global': 'global',
}

# global lessons 的父节点（不连 domain 而连 orchestrator）
GLOBAL_PARENT = 'hermes_orchestrator'


def slugify(text: str) -> str:
    """生成图节点安全的 ID slug。"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text[:48].rstrip('-')


def parse_lessons_from_file(filepath: Path) -> list[dict]:
    """解析单个 lesson .md，返回 [{title, severity, body, domain, content_hash}]"""
    lessons = []
    text = filepath.read_text(encoding='utf-8', errors='replace')
    domain = filepath.stem  # 'ops-domain', 'global', etc.

    current_severity = 'MEDIUM'
    current_title = ''
    current_body = []

    def flush():
        if current_title:
            content = '\n'.join(current_body).strip() if current_body else ''
            h = hashlib.md5(f'{domain}|{current_severity}|{current_title}'.encode()).hexdigest()[:12]
            lessons.append({
                'title': current_title,
                'severity': current_severity,
                'body': content,
                'domain': domain,
                'content_hash': h,
            })

    for line in text.split('\n'):
        stripped = line.strip()
        # 检测 severity header
        if stripped.startswith('## '):
            for key, val in SEVERITY_MAP.items():
                if key in stripped:
                    flush()
                    current_severity = val
                    current_title = ''
                    current_body = []
                    break
            else:
                # 普通 ## 标题（非 severity），刷新但不改变 severity
                flush()
                current_title = ''
                current_body = []
        elif stripped.startswith('### '):
            flush()
            current_title = stripped.replace('### ', '').strip()
            current_body = []
        elif current_title and stripped:
            current_body.append(stripped)

    flush()
    return lessons


def load_graph(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if 'nodes' not in data:
        data['nodes'] = []
    if 'links' not in data:
        data['links'] = []
    return data


def save_graph(data: dict, path: str):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'  ✅ 图已保存: {path}')


def main():
    parser = argparse.ArgumentParser(description='Lessons → Graphify 夜间同步脚本')
    parser.add_argument('--graph', default=DEFAULT_GRAPH, help=f'graph.json 路径 (默认: {DEFAULT_GRAPH})')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不写入')
    args = parser.parse_args()

    print(f'📘 Lessons → Graphify 同步')
    print(f'   源: {LESSONS_DIR}')
    print(f'   目标: {args.graph}{" (DRY RUN)" if args.dry_run else ""}')
    print()

    # 1. 加载已有 graph
    graph = load_graph(args.graph)
    existing_nodes = graph['nodes']
    existing_edges = graph['links']

    # 构建已有 content hash 集合用于去重
    existing_hashes = set()
    for n in existing_nodes:
        ch = n.get('properties', {}).get('content_hash', '') if isinstance(n.get('properties'), dict) else ''
        if ch:
            existing_hashes.add(ch)

    # 2. 扫描所有 lesson 文件
    lesson_files = sorted(LESSONS_DIR.glob('*.md'))
    parsed = []
    for fpath in lesson_files:
        if SKIP_FILES.match(fpath.name):
            print(f'  ⏭️  跳过: {fpath.name}')
            continue
        lessons = parse_lessons_from_file(fpath)
        print(f'  📄 {fpath.name}: {len(lessons)} 条教训')
        parsed.extend(lessons)

    print(f'\n  共解析 {len(parsed)} 条教训')
    print()

    # 3. 去重
    new_lessons = [l for l in parsed if l['content_hash'] not in existing_hashes]
    print(f'  已有 {len(existing_hashes)} 条已同步，新增 {len(new_lessons)} 条')

    if not new_lessons:
        print('\n✅ 没有需要同步的新教训')
        return

    # 4. 创建新节点和边
    new_nodes = []
    new_edges = []
    added = 0

    for l in new_lessons:
        domain = l['domain']
        parent_id = DOMAIN_NODE_MAP.get(domain)

        # 生成节点 ID
        if domain == 'global':
            node_id = f"lesson_{slugify(l['title'])}"
            # 避免与现有 global lesson 节点冲突
            if any(n['id'] == node_id for n in existing_nodes):
                # 已存在同名节点但 content hash 不同 → 加后缀
                node_id = f"lesson_{slugify(l['title'])}_{l['content_hash']}"
        else:
            node_id = f"{domain.replace('-', '_')}_lesson_{slugify(l['title'])}"
            if any(n['id'] == node_id for n in existing_nodes):
                node_id = f"{domain.replace('-', '_')}_lesson_{slugify(l['title'])}_{l['content_hash']}"

        if args.dry_run:
            print(f'  📝 新增: {node_id}')
            print(f'      标题: {l["title"]}')
            print(f'      域: {domain} → 父节点: {parent_id or "?"}')
            continue

        # 构造自然语言的 label：去掉 item 列表中常见的编号/冒号前缀
        lesson_label = l['title'].lstrip('0123456789.、：:（(）)').strip()
        node = {
            'id': node_id,
            'label': lesson_label,
            'file_type': 'lesson',
            'source_file': f'lessons/{domain}.md',
            'norm_label': l['title'].lower().strip(),
            'community': None,
            'properties': {
                'severity': l['severity'],
                'domain': domain,
                'content_hash': l['content_hash'],
                'synced_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
            }
        }
        new_nodes.append(node)

        # 创建边: 连接父节点
        if domain == 'global' and GLOBAL_PARENT:
            edge = {
                'source': GLOBAL_PARENT,
                'target': node_id,
                'relation': 'applies_to',
                'confidence': 'EXTRACTED',
                'confidence_score': 1.0,
                'weight': 1.0,
            }
            new_edges.append(edge)
        elif parent_id:
            edge = {
                'source': parent_id,
                'target': node_id,
                'relation': 'contains',
                'confidence': 'EXTRACTED',
                'confidence_score': 1.0,
                'weight': 1.0,
            }
            new_edges.append(edge)

        added += 1

    if args.dry_run:
        print(f'\n📋 Dry run 完成 — 将新增 {added} 个节点, {len(new_edges)} 条边')
        return

    # 5. 写入
    graph['nodes'].extend(new_nodes)
    graph['links'].extend(new_edges)
    save_graph(graph, args.graph)

    print(f'\n📋 同步完成:')
    print(f'   新增节点: {added}')
    print(f'   新增边:   {len(new_edges)}')
    print(f'   总节点:   {len(graph["nodes"])}')
    print(f'   总边:     {len(graph["links"])}')
    print()
    print(f'   域名 → 节点ID 映射:')
    for domain, nid in DOMAIN_NODE_MAP.items():
        count = sum(1 for n in graph['nodes'] if n.get('properties', {}).get('domain') == domain)
        print(f'     {domain} → {nid} ({count} lessons)')


if __name__ == '__main__':
    main()
