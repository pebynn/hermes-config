#!/usr/bin/env python3
"""
pipeline_runner.py — cron 驱动的 Pipeline 引擎

每15-30分钟由 cron 触发一次，检查所有活跃 pipeline：
- 当前 stage 未开始 → 执行脚本
- 当前 stage 已完成 → 验证产出 → 推进到下一 stage
- 当前 stage 失败 → 记录错误，发通知
- 当前 stage 是 L3 → 暂停，等用户决策

用法:
  python3 pipeline_runner.py tick       # cron 调用，执行一次推进
  python3 pipeline_runner.py status     # 查看所有 pipeline 状态
  python3 pipeline_runner.py resume <id># 手动推进 L3 暂停的 pipeline
  python3 pipeline_runner.py define <yaml_path>  # 从 yaml 定义新 pipeline
"""
import json, sys, subprocess, os, re
from datetime import datetime
from pathlib import Path
import traceback

HOME = Path.home()
PIPELINE_FILE = HOME / '.hermes' / 'agenda' / 'pipelines.json'
TASKS_DIR = HOME / '.hermes' / 'agenda' / 'pipeline-tasks'


def load():
    if PIPELINE_FILE.exists():
        try:
            return json.loads(PIPELINE_FILE.read_text())
        except:
            traceback.print_exc()
            pass
    return {"pipelines": [], "last_tick": None}


def save(data):
    data["last_tick"] = datetime.now().strftime('%Y-%m-%d %H:%M')
    PIPELINE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def run_script(script_cmd, workdir=None, timeout=300):
    """执行一个 stage 脚本，返回 (ok, output)"""
    try:
        r = subprocess.run(
            script_cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=workdir or str(HOME)
        )
        output = (r.stdout or "") + "\n" + (r.stderr or "")
        output = output.strip()
        ok = r.returncode == 0
        return ok, output[:2000]  # 截断防爆
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT ({timeout}s)"
    except Exception as e:
        traceback.print_exc()
        return False, str(e)


def verify_stage(stage):
    """验证 stage 产出"""
    verify = stage.get("verify", "")
    if not verify:
        return True, "无验证条件"

    # 支持简单模式: "file exists:/path/to/file"
    if verify.startswith("file exists:"):
        path = verify.replace("file exists:", "").strip()
        path = os.path.expanduser(path)
        ok = Path(path).exists()
        return ok, f"{'存在' if ok else '不存在'}: {path}"

    # shell 命令模式：exit 0 = 通过
    ok, out = run_script(verify)
    return ok, out[:500]


def notify_user(message):
    """通知用户 pipeline 状态变更（输出到 stdout → cron deliver 拾取）"""
    # 避免同一条通知反复发
    notify_file = HOME / '.hermes' / 'agenda' / '.pipeline_notify'
    last_msg = ""
    if notify_file.exists():
        last_msg = notify_file.read_text().strip()

    if last_msg == message[:200]:
        return  # 同一条不重复发

    # 写入通知文件 + 标记已发
    notify_file.write_text(message[:200])

    # 输出到 stdout → cron deliver 拾取 → QQ Bot
    print(f"[pipeline] {message}")

    # 也写入 task_tracker 让 agenda 拾取
    tracker_file = HOME / '.hermes' / 'agenda' / 'task_tracker.json'
    # ... (existing logic)
    if tracker_file.exists():
        try:
            tracker = json.loads(tracker_file.read_text())
        except:
            traceback.print_exc()
            tracker = {"tasks": []}
    else:
        tracker = {"tasks": []}

    # 避免重复通知
    for t in tracker.get("tasks", []):
        if message[:40] in t.get("desc", ""):
            return

    task = {
        "id": f"pipeline-notify-{datetime.now().strftime('%H%M%S')}",
        "desc": f"🚨 {message}",
        "added": datetime.now().strftime('%Y-%m-%d'),
        "last_seen": datetime.now().strftime('%Y-%m-%d'),
        "days_pending": 0,
        "priority": "P1",
        "tags": ["pipeline"],
        "source": "pipeline_runner"
    }
    tracker.setdefault("tasks", []).append(task)
    tracker_file.write_text(json.dumps(tracker, indent=2, ensure_ascii=False))


def deliver_queued_notifications():
    """扫描 notify_queue/ 中的 JSON 文件，投递到 QQ Bot（stdout → cron deliver）

    每个文件格式: {"title": "...", "body": "...", "priority": "P1", "timestamp": "..."}
    投递后删除文件，避免重复。
    """
    queue_dir = HOME / '.hermes' / 'notify_queue'
    if not queue_dir.exists():
        return

    files = sorted(queue_dir.glob("*.json"))
    if not files:
        return

    delivered = 0
    for f in files:
        try:
            data = json.loads(f.read_text())
            title = data.get("title", "")
            body = data.get("body", "")
            msg = f"{title}\n{body}" if body else title
            print(msg)  # stdout → cron deliver → QQ Bot
            f.unlink()  # 删除已投递
            delivered += 1
        except Exception:
            # 解析失败的文件可能是损坏的，也删除避免堆积
            try:
                f.unlink()
            except Exception:
                pass

    # 如果投递了多条，之间用分隔符
    if delivered > 1:
        pass  # cron deliver 会逐行发送，不需要额外分隔


def tick():
    """cron 调用：推进所有活跃 pipeline"""
    data = load()
    changed = False

    for pl in data["pipelines"]:
        if pl["status"] not in ("running", "paused"):
            continue

        if pl["status"] == "paused":
            continue  # 等待用户决策

        current = pl.get("current", 1)
        stages = pl.get("stages", [])
        if current > len(stages):
            pl["status"] = "completed"
            pl["completed_at"] = datetime.now().strftime('%Y-%m-%d %H:%M')
            notify_user(f"Pipeline 完成: {pl.get('goal','')[:80]}")
            changed = True
            continue

        stage = stages[current - 1]
        script = stage.get("script", "")
        level = stage.get("level", "L1")

        if not script:
            # 没有脚本的 stage
            if level == "L3":
                # 检查是否刚被 resume
                if pl.get("status") == "running":
                    # 跳过无脚本 L3 stage
                    pl["current"] = current + 1
                    stage["completed_at"] = datetime.now().strftime('%Y-%m-%d %H:%M')
                    stage["output"] = "用户已决策，跳过"
                    if pl["current"] > len(stages):
                        pl["status"] = "completed"
                        pl["completed_at"] = datetime.now().strftime('%Y-%m-%d %H:%M')
                        notify_user(f"Pipeline 完成: {pl.get('goal','')[:80]}")
                        print(f"    ✅ L3 已决策，pipeline 完成")
                    else:
                        print(f"    ✅ L3 已决策，推进到 stage {pl['current']}")
                    changed = True
                    continue
                else:
                    # 第一次到达 L3，暂停
                    pl["status"] = "paused"
                    pl["waiting_since"] = datetime.now().strftime('%Y-%m-%d %H:%M')
                    notify_user(f"Pipeline '{pl.get('goal','')[:60]}' 到 stage {current} ({stage.get('desc','')})，等待决策")
                    changed = True

            elif level == "WAIT":
                # 等待时间到——无脚本，只有 until 条件
                until = stage.get("until", "")
                if not until:
                    print(f"    ⚠️ WAIT stage 缺少 until 字段", file=sys.stderr)
                    # 没有 until 就跳过
                    pl["current"] = current + 1
                    stage["completed_at"] = datetime.now().strftime('%Y-%m-%d %H:%M')
                    stage["output"] = "无条件 WAIT，跳过"
                    changed = True
                else:
                    # 解析 until: "7d" 或 "2026-05-16" 或 "2026-05-16T00:00"
                    target = None
                    now = datetime.now()

                    # 尝试解析为 ISO 日期
                    try:
                        if 'T' in until:
                            target = datetime.strptime(until, '%Y-%m-%dT%H:%M')
                        else:
                            target = datetime.strptime(until, '%Y-%m-%d')
                    except:
                        traceback.print_exc()
                        pass

                    # 尝试解析为相对时间 "Nd"
                    if target is None and until.endswith('d'):
                        import re as re2
                        m = re2.match(r'(\d+)d', until)
                        if m:
                            from datetime import timedelta as td
                            target = now + td(days=int(m.group(1)))

                    if target is None:
                        print(f"    ⚠️ 无法解析 WAIT until: {until}", file=sys.stderr)
                        pl["current"] = current + 1
                        changed = True
                    elif now >= target:
                        print(f"    ✅ WAIT 到期 ({until})，推进到 stage {current + 1}")
                        pl["current"] = current + 1
                        stage["completed_at"] = now.strftime('%Y-%m-%d %H:%M')
                        stage["output"] = f"等待至 {until}，到期自动推进"
                        changed = True
                    else:
                        remaining = (target - now).days
                        print(f"    ⏳ WAIT 未到期 ({until}, 还剩 {remaining} 天)，下次 tick 再检查", file=sys.stderr)
            continue

        # 执行脚本
        print(f"  [tick] pipeline={pl['id']} stage={current} script={script[:60]}...", file=sys.stderr)
        ok, output = run_script(script, stage.get("workdir"))

        if not ok:
            # 失败——记录但继续（重试机制）
            pl.setdefault("retries", {})
            r = pl["retries"].get(str(current), 0) + 1
            pl["retries"][str(current)] = r
            pl["last_error"] = output[:500]
            pl["error_at"] = datetime.now().strftime('%Y-%m-%d %H:%M')

            if r >= 2:
                pl["status"] = "failed"
                pl["failed_at"] = datetime.now().strftime('%Y-%m-%d %H:%M')
                notify_user(f"Pipeline 失败: {pl.get('goal','')[:60]} | stage {current} 重试{r}次: {output[:200]}")
            else:
                print(f"    ⚠️ 失败(第{r}次)，下次 tick 重试: {output[:200]}", file=sys.stderr)
            changed = True
            continue

        # 验证产出
        verify_ok, verify_msg = verify_stage(stage)
        if not verify_ok:
            pl["status"] = "failed"
            pl["failed_at"] = datetime.now().strftime('%Y-%m-%d %H:%M')
            pl["last_error"] = f"验证失败 (stage {current}): {verify_msg[:300]}"
            notify_user(f"Pipeline 验证失败: {pl.get('goal','')[:60]} | stage {current}: {verify_msg[:200]}")
            changed = True
            continue

        # 成功，推进
        pl["current"] = current + 1
        stage["completed_at"] = datetime.now().strftime('%Y-%m-%d %H:%M')
        stage["output"] = output[:500]

        # 检查下一个 stage 是否 L3
        next_stage = stages[pl["current"] - 1] if pl["current"] <= len(stages) else None
        if next_stage and next_stage.get("level") == "L3":
            pl["status"] = "paused"
            pl["waiting_since"] = datetime.now().strftime('%Y-%m-%d %H:%M')
            notify_user(f"Pipeline '{pl.get('goal','')[:60]}' 到 stage {pl['current']} ({next_stage.get('desc','')})，等待决策")
        elif pl["current"] > len(stages):
            pl["status"] = "completed"
            pl["completed_at"] = datetime.now().strftime('%Y-%m-%d %H:%M')
            notify_user(f"Pipeline 完成: {pl.get('goal','')[:80]}")

        print(f"    ✅ stage {current} 完成 → 推进到 {pl['current']}")
        changed = True

    if changed:
        save(data)

    # 统计
    running = [p for p in data["pipelines"] if p["status"] == "running"]
    paused = [p for p in data["pipelines"] if p["status"] == "paused"]
    failed = [p for p in data["pipelines"] if p["status"] == "failed"]
    completed = [p for p in data["pipelines"] if p["status"] == "completed"]

    # 只在有变化时输出（cron deliver 会拾取 stdout → QQ Bot）
    new_completions = [p for p in data["pipelines"] if p.get("status") == "completed" and p.get("completed_at", "").startswith(datetime.now().strftime('%Y-%m-%d'))] if changed else []
    new_failures = [p for p in data["pipelines"] if p.get("status") == "failed" and datetime.now().timestamp() - (datetime.strptime(p.get("failed_at", "2000-01-01"), '%Y-%m-%d %H:%M').timestamp() if ' ' in p.get("failed_at", "") else 0) < 120] if changed else []

    if new_completions:
        for p in new_completions:
            print(f"✅ Pipeline 完成: {p.get('goal','')[:80]}")
    if new_failures:
        for p in new_failures:
            print(f"❌ Pipeline 失败: {p.get('goal','')[:80]} — {p.get('last_error','')[:150]}")

    # 安静模式：无事件不输出（避免每30分钟刷屏）

    # ── 投递队列通知（来自所有脚本的 notify.send() 调用）──
    deliver_queued_notifications()


def resume(pipeline_id):
    """手动恢复一个暂停的 pipeline（用户决策后调用）"""
    data = load()
    for pl in data["pipelines"]:
        if pl["id"] == pipeline_id or pipeline_id in pl.get("goal", ""):
            if pl["status"] != "paused":
                print(f"Pipeline {pl['id']} 不在暂停状态 (当前={pl['status']})")
                return
            pl["status"] = "running"
            pl["resumed_at"] = datetime.now().strftime('%Y-%m-%d %H:%M')
            save(data)
            print(f"✅ Pipeline '{pl.get('goal','')[:60]}' 已恢复")
            # 立即 tick 一次
            tick()
            return

    print(f"⚠️ 未找到 pipeline: {pipeline_id}")


def status():
    """列出所有 pipeline"""
    data = load()
    if not data["pipelines"]:
        print("(无活跃 pipeline)")
        return

    for pl in data["pipelines"]:
        icon = {"running": "▶️", "paused": "⏸️", "failed": "❌", "completed": "✅"}.get(pl["status"], "❓")
        current = pl.get("current", 1)
        total = len(pl.get("stages", []))
        goal = pl.get("goal", "")[:80]
        print(f"  {icon} [{pl['status']}] {current}/{total} — {goal}")
        if pl.get("last_error"):
            print(f"     └─ 错误: {pl['last_error'][:150]}")
        if pl.get("waiting_since"):
            print(f"     └─ 等待决策自: {pl['waiting_since']}")
        for s in pl.get("stages", []):
            done = "✅" if s.get("completed_at") else "⬜"
            lvl = s.get("level", "L2")
            print(f"       {done} [{lvl}] {s.get('desc','')[:60]}")


def define(goal, stages, pipeline_id=None):
    """定义新 pipeline"""
    data = load()
    pl = {
        "id": pipeline_id or f"pipe-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "goal": goal,
        "stages": stages,
        "current": 1,
        "status": "running",
        "retries": {},
        "created": datetime.now().strftime('%Y-%m-%d %H:%M'),
    }
    data["pipelines"].append(pl)
    save(data)
    print(f"✅ Pipeline 已定义: {pl['id']} ({len(stages)} stages)")
    # 立即 tick 第一次
    tick()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: pipeline_runner.py <tick|status|resume|define> [args...]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "tick":
        tick()
    elif cmd == "status":
        status()
    elif cmd == "resume" and len(sys.argv) > 2:
        resume(sys.argv[2])
    elif cmd == "define":
        # 从 stdin 读取 JSON 定义
        import json as j
        try:
            desc = j.loads(sys.stdin.read())
            define(desc.get("goal",""), desc.get("stages",[]), desc.get("id"))
        except Exception as e:
            print(f"❌ 解析失败: {e}")
            print('期望 JSON: {"goal": "...", "stages": [...]}')
    else:
        print(f"未知命令: {cmd}")
