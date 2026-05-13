#!/home/pebynn/tools/quant_env/bin/python3
"""
MCP 进程自动清理脚本 — 每个 MCP server 只保留最新的1个进程。
v1.0 2026-05-13
"""
import os
import sys
import subprocess
import re
from collections import defaultdict


def get_mcp_processes():
    """获取所有 MCP 相关进程，按 server 名称分组。"""
    out = subprocess.run(
        ["ps", "aux"],
        capture_output=True, text=True, timeout=10
    ).stdout

    servers = defaultdict(list)
    for line in out.splitlines():
        if "grep" in line:
            continue
        # 匹配 mcp-*.py 或 mcp-server-* 进程
        m = re.search(r'(mcp-\S+\.py|mcp-server-\S+|stock-mcp|stock-sdk)', line)
        if m:
            name = m.group(1)
            pid = int(line.split()[1])
            try:
                start_time = line.split()[8]  # ps aux TIME field
            except IndexError:
                start_time = "00:00"
            servers[name].append((pid, start_time))

    # uv tool 进程和 npm exec 包装进程也需要清理
    uv_mcp = defaultdict(list)
    node_mcp = defaultdict(list)
    for line in out.splitlines():
        if "grep" in line:
            continue
        # uv tool mcp-server-time
        if "mcp-server-time" in line and "uv tool" not in line:
            # This is the python child of uv tool
            pass  # handeled by mcp-server-time group above
        # node wrapper process
        if "npm exec" in line and "mcp" in line.lower():
            pid = int(line.split()[1])
            node_mcp["npm-exec-mcp"].append(pid)

    return servers, node_mcp


def deduplicate(servers):
    """每个 server 只保留最新的进程，杀掉多余的。"""
    killed = 0
    for name, procs in servers.items():
        if len(procs) <= 1:
            continue
        # 按时间排序，保留最晚启动的
        procs_sorted = sorted(procs, key=lambda x: x[1], reverse=True)
        keep_pid = procs_sorted[0][0]
        to_kill = [p[0] for p in procs_sorted[1:]]
        for pid in to_kill:
            try:
                os.kill(pid, 15)  # SIGTERM
                killed += 1
            except ProcessLookupError:
                pass
        if to_kill:
            print(f"  [{name}] 保留 PID={keep_pid}, 清理 {len(to_kill)} 个冗余进程", file=sys.stderr)
    return killed


def main():
    # 静默模式：只在有清理动作时输出
    servers, node_mcp = get_mcp_processes()

    kill_count = deduplicate(servers)

    # 清理 npm exec 包装进程 (每个最多保留1个)
    for name, pids in node_mcp.items():
        if len(pids) > 1:
            for pid in pids[1:]:
                try:
                    os.kill(pid, 15)
                    kill_count += 1
                except ProcessLookupError:
                    pass

    # 只在有动作时输出到 stdout (cron才会投递)
    if kill_count > 0:
        print(f"MCP清理: 杀掉 {kill_count} 个冗余进程")
    # 无动作时 stdout 静默 → cron 不投递


if __name__ == "__main__":
    main()
