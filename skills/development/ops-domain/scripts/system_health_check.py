#!/usr/bin/env python3
"""系统健康检查脚本 - Hermes Agent"""

import json
import subprocess
import os
import time


def run_cmd(cmd):
    """执行 shell 命令并返回 stdout"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip()
    except Exception as e:
        return f"检查失败: {e}"


def check_disk():
    """检查磁盘使用率"""
    try:
        output = run_cmd("df -h | awk 'NR>1 {print $NF, $5}'")
        mounts = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                mount_point = parts[0]
                usage_str = parts[1].rstrip("%")
                if usage_str == "" or usage_str == "-":
                    continue
                usage = int(float(usage_str))
                mounts.append({
                    "挂载点": mount_point,
                    "使用率": usage,
                    "状态": "紧急" if usage > 90 else ("警告" if usage > 80 else "正常")
                })
        return mounts if mounts else [{"挂载点": "无", "使用率": 0, "状态": "正常"}]
    except Exception as e:
        return f"检查失败: {e}"


def check_memory():
    """检查内存使用情况"""
    try:
        output = run_cmd("free -m | awk 'NR==2 {print $2, $NF}'")
        parts = output.split()
        if len(parts) >= 2:
            total = int(parts[0])
            available = int(parts[1])
            ratio = round(available / total * 100, 1) if total > 0 else 0
            status = "危险" if ratio < 10 else ("警告" if ratio < 20 else "正常")
            return {"总MB": total, "可用MB": available, "可用率": ratio, "状态": status}
        return {"总MB": 0, "可用MB": 0, "可用率": 0, "状态": "检查失败"}
    except Exception as e:
        return f"检查失败: {e}"


def check_cpu():
    """检查 CPU 负载"""
    try:
        output = run_cmd("uptime | awk -F'load average:' '{print $2}'")
        parts = [x.strip() for x in output.split(",")]
        if len(parts) >= 3:
            return {"1min": float(parts[0]), "5min": float(parts[1]), "15min": float(parts[2])}
        return {"1min": 0, "5min": 0, "15min": 0}
    except Exception as e:
        return f"检查失败: {e}"


def check_hermes_process():
    """检查 Hermes 进程"""
    try:
        output = run_cmd("pgrep -f hermes 2>/dev/null || true")
        pids = [p.strip() for p in output.splitlines() if p.strip()]
        pid_count = len(pids)
        return {"运行": pid_count > 0, "PID数": pid_count}
    except Exception as e:
        return {"运行": False, "PID数": 0}


def check_docker():
    """检查 Docker 容器状态"""
    try:
        total_str = run_cmd("docker ps -a -q 2>/dev/null | wc -l")
        running_str = run_cmd("docker ps -q 2>/dev/null | wc -l")
        total = int(total_str.strip()) if total_str and total_str != "检查失败" else 0
        running = int(running_str.strip()) if running_str and running_str != "检查失败" else 0
        status = "警告" if running == 0 and total > 0 else "正常"
        return {"容器数": total, "运行中": running, "状态": status}
    except Exception as e:
        return {"容器数": 0, "运行中": 0, "状态": "检查失败"}


def check_cron():
    """检查 Cron 任务状态"""
    try:
        cron_dir = os.path.expanduser("~/.hermes/cron")
        if not os.path.isdir(cron_dir):
            return {"总数": 0, "异常": 0}
        total = 0
        abnormal = 0
        for fname in os.listdir(cron_dir):
            fpath = os.path.join(cron_dir, fname)
            if os.path.isfile(fpath):
                total += 1
                try:
                    # 尝试解析/执行检查
                    if not os.access(fpath, os.R_OK):
                        abnormal += 1
                except Exception:
                    abnormal += 1
        return {"总数": total, "异常": abnormal}
    except Exception as e:
        return {"总数": 0, "异常": 0}


def check_uptime():
    """检查系统运行时间"""
    try:
        output = run_cmd("uptime -p 2>/dev/null || uptime | awk -F'up ' '{print $2}' | awk -F',' '{print $1}'")
        # Clean up "up " prefix if present
        output = output.replace("up ", "").strip()
        if not output:
            output = "N/A"
        return output
    except Exception as e:
        return "检查失败"


def main():
    now = time.strftime("%Y-%m-%d %H:%M", time.localtime())

    disk = check_disk()
    memory = check_memory()
    cpu = check_cpu()
    hermes_proc = check_hermes_process()
    docker = check_docker()
    cron = check_cron()
    uptime_val = check_uptime()

    # 生成告警
    alerts = []

    # 磁盘告警
    if isinstance(disk, list):
        for m in disk:
            if m["状态"] == "紧急":
                alerts.append(f"磁盘紧急: {m['挂载点']} 使用率 {m['使用率']}%")
            elif m["状态"] == "警告":
                alerts.append(f"磁盘警告: {m['挂载点']} 使用率 {m['使用率']}%")

    # 内存告警
    if isinstance(memory, dict):
        if memory.get("状态") == "危险":
            alerts.append(f"内存危险: 可用率 {memory.get('可用率', '?')}%")
        elif memory.get("状态") == "警告":
            alerts.append(f"内存警告: 可用率 {memory.get('可用率', '?')}%")

    # Docker 告警
    if isinstance(docker, dict):
        if docker.get("状态") == "警告":
            alerts.append("Docker: 有容器但无容器在运行")
        elif docker.get("状态") == "检查失败":
            alerts.append("Docker: 检查失败")

    # Hermes 进程告警
    if isinstance(hermes_proc, dict) and not hermes_proc.get("运行", False):
        alerts.append("Hermes 进程未运行")

    # Cron 异常告警
    if isinstance(cron, dict) and cron.get("异常", 0) > 0:
        alerts.append(f"Cron 任务有 {cron['异常']} 个异常")

    # 总评
    danger_count = sum(1 for a in alerts if "紧急" in a or "危险" in a)
    warning_count = sum(1 for a in alerts if "警告" in a)
    if danger_count > 0:
        overall = "危险"
    elif warning_count > 0:
        overall = "警告"
    else:
        overall = "健康"

    result = {
        "时间": now,
        "磁盘": disk,
        "内存": memory,
        "CPU负载": cpu,
        "进程": {"hermes": hermes_proc},
        "Docker": docker,
        "Cron任务": cron,
        "运行时间": uptime_val,
        "总评": overall,
        "告警": alerts
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
