#!/usr/bin/env python3
"""跨域影响分析 — 修改前自动检测影响面
在 kanban_create 前或 patch/write_file 前运行。
用法: python3 cross_domain_impact.py --files <file1> <file2> ... 
      或作为 pre_change hook 自动触发
"""
import subprocess
import sys
import json
import os

def graph_search(query):
    """调用 graphify MCP 搜索相关节点"""
    # 通过 JSON-RPC 风格调用 MCP
    result = subprocess.run(
        ['python3', '-c', f'''
import sys
sys.path.insert(0, "{os.path.expanduser('~/.hermes/mcp-servers')}")
# 直接读取 graph.json 搜索
import json
with open("{os.path.expanduser('~/brain/graphify-out/graph.json')}") as f:
    g = json.load(f)
q = "{query}".lower()
hits = []
for nid, node in g.get("nodes", {{}}).items():
    label = (node.get("label") or "").lower()
    props = str(node.get("properties", {{}})).lower()
    if q in label or q in props:
        hits.append({{"id": nid, "label": node.get("label"), "type": node.get("type")}})
        if len(hits) >= 20:
            break
print(json.dumps(hits))
'''], capture_output=True, text=True, timeout=30)
    try:
        return json.loads(result.stdout)
    except:
        return []

def find_dependencies(files):
    """根据文件路径查找graph中的依赖节点"""
    all_deps = {}
    for f in files:
        basename = os.path.basename(f).replace('.py', '').replace('.md', '').replace('.sh', '')
        hits = graph_search(basename)
        if hits:
            all_deps[f] = hits
    return all_deps

def main():
    import argparse
    parser = argparse.ArgumentParser(description='跨域影响分析')
    parser.add_argument('--files', nargs='+', required=True, help='即将修改的文件列表')
    parser.add_argument('--domain', default='general', help='当前域')
    args = parser.parse_args()
    
    print(f"=== 跨域影响分析 ===")
    print(f"修改文件: {args.files}")
    print(f"当前域: {args.domain}")
    print()
    
    deps = find_dependencies(args.files)
    
    if not deps:
        print("✅ 未发现跨域依赖，可以安全修改。")
        return 0
    
    # 按域分组
    domain_deps = {}
    for f, hits in deps.items():
        for h in hits:
            dtype = h.get('type', 'unknown')
            if dtype not in domain_deps:
                domain_deps[dtype] = []
            domain_deps[dtype].append(h)
    
    print("⚠️  发现以下跨域依赖：")
    for domain, hits in domain_deps.items():
        if domain != args.domain and domain != 'unknown':
            print(f"  🔗 {domain}域: {len(hits)}个节点受影响")
            for h in hits[:3]:
                print(f"     - {h.get('label', h['id'])}")
    
    if any(d != args.domain for d in domain_deps if d != 'unknown'):
        print()
        print("🔴 建议：修改前先评估跨域影响，必要时通知相关域维护者。")
        return 1
    
    print()
    print("⚠️  同域内依赖，可继续修改但需注意。")
    return 0

if __name__ == '__main__':
    sys.exit(main())
