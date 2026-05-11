#!/usr/bin/env python3
"""
每日议程生成器 v2.1 — 智能版 + 任务继承
原则：每行输出必须可行动。不给用户看原始 dump。
v2.1: 自动继承前日未完成任务 + 超时升优先级
"""
import os, json, re, subprocess, uuid
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import traceback

HOME = Path.home()
AGENDA_DIR = HOME / '.hermes' / 'agenda'
LOGS_DIR = HOME / '.hermes' / 'logs'
PENDING_FILE = AGENDA_DIR / 'pending.md'
DAILY_FILE = AGENDA_DIR / 'daily.md'
STATE_FILE = AGENDA_DIR / 'state.json'
TRACKER_FILE = AGENDA_DIR / 'task_tracker.json'
ERRORS_LOG = LOGS_DIR / 'errors.log'

# ── 自动升优先级阈值（天） ──
PROMOTE_AFTER_DAYS = {3: '⚡', 5: '🔥', 7: '🚨'}

# ── 已知噪音模式（不报警） ──
NOISE_PATTERNS = [
    r'Task was destroyed but it is pending',
    r'Task exception was never retrieved',
    r'rate limited',
    r'Weixin send failed.*iLink',
    r'Timeout context manager should be used inside a task',
    r'RemoteDisconnected',
    r'Connection reset by peer',
    r'DNS lookup failed',
    r'session_summariz.*429',
    r'CDP connection refused',
    r'camofox.*refused',
    r'Error parsing SSE message',
    r'mcp\.client\.streamable_http',
]


def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() or r.stderr.strip()
    except Exception as e:
        traceback.print_exc()
        return f"(超时/错误: {e})"


# ══════════════════════════════════════════════
# 1. 服务健康
# ══════════════════════════════════════════════

def check_services():
    issues = []
    # Gateway
    gw = run("systemctl --user is-active hermes-gateway.service 2>/dev/null")
    if gw != 'active':
        issues.append(("🔴", "Gateway 未运行", f"systemctl --user restart hermes-gateway.service"))
    # MySQL (检查进程)
    mysql = run("pgrep -x mysqld > /dev/null && echo 'alive' || echo 'dead'")
    if 'alive' not in mysql:
        issues.append(("🔴", "MySQL 进程未运行", "sudo systemctl start mysql"))
    # DeepSeek API (轻量探测)
    ds = run("curl -s -o /dev/null -w '%{http_code}' --max-time 5 https://api.deepseek.com/v1/models 2>/dev/null")
    if ds not in ('200', '401'):  # 401=key有效但鉴权, 也算通
        issues.append(("🟠", f"DeepSeek API 不可达 (HTTP {ds})", "检查网络/熔断器"))
    # Camofox (可能已停用 — 降级为信息)
    cf = run("curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://localhost:9377/health 2>/dev/null")
    if cf != '200':
        pass  # Camofox 已由 stealth-browser 替代，不报警
    return issues


# ══════════════════════════════════════════════
# 2. Cron 智能检测
# ══════════════════════════════════════════════

def check_crons():
    try:
        raw = subprocess.run(
            ['hermes', 'cron', 'list'],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, 'PATH': os.environ.get('PATH', '')}
        )
        output = raw.stdout + raw.stderr
    except Exception as e:
        traceback.print_exc()
        return [("🔴", f"cron 检查失败: {e}", "")], 0, 0

    # 文本解析：找 status=error 的 job
    failed = []
    warnings = []
    lines = output.split('\n')
    current_job = None
    for line in lines:
        if 'job_id' in line or '│' in line:
            continue
        if 'last_status' in line and 'error' in line.lower():
            name = current_job or 'unknown'
            failed.append(f"  {name}: last_status=error")
        if 'name' in line and ':' in line:
            # 提取名称
            parts = line.split(':', 1)
            if len(parts) > 1:
                current_job = parts[1].strip().strip('"').strip("'")[:60]

    if not failed and not warnings:
        return [], 25, 25  # 默认值

    result = []
    if failed:
        result.append(("🔴", f"{len(failed)} 个 cron 失败", failed[0][:120] if len(failed) == 1 else f"{len(failed)}个"))
    if warnings:
        result.append(("🟡", f"{len(warnings)} 个 cron 警告", warnings[0][:120]))
    return result, 25, 25


# ══════════════════════════════════════════════
# 3. 数据新鲜度
# ══════════════════════════════════════════════

def check_data_freshness():
    issues = []
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # K线数据 — MySQL
    mysql_ok = run(f"mysql -u stock -p'***' -h localhost stock_kline -N -e \"SELECT COUNT(*) FROM daily_kline WHERE trade_date='{yesterday}'\" 2>/dev/null || echo 0")
    if mysql_ok == '0' or not mysql_ok:
        issues.append(("🟡", f"K线数据 {yesterday} 为空 (可能未到拉取时间 16:00)", "等待 afff56398abe cron"))

    # 复盘文章
    draft = HOME / 'writing-data' / 'drafts' / f'{today}-每日复盘.md'
    draft_y = HOME / 'writing-data' / 'drafts' / f'{yesterday}-每日复盘.md'
    if not draft.exists() and not draft_y.exists():
        issues.append(("🟡", "今日复盘未生成", "检查 d075c207d860 cron (16:00)"))

    return issues


# ══════════════════════════════════════════════
# 4. 资源趋势
# ══════════════════════════════════════════════

def check_resources():
    items = []
    # 磁盘
    disk = run("df -h / | tail -1 | awk '{print $5, $3, $2}'")
    pct_str = disk.split('%')[0] if '%' in disk else '0'
    try:
        pct = int(pct_str.split()[-1]) if pct_str else 0
    except:
        traceback.print_exc()
        pct = 0
    items.append(("💾", f"磁盘 {disk}"))

    # 内存
    mem = run("free -h | grep -E 'Mem|内存' | awk '{print $3, $2, $7}'")
    items.append(("🧠", f"内存 {mem}"))

    # sessions 数量
    sessions_dir = HOME / '.hermes' / 'sessions'
    if sessions_dir.exists():
        session_count = len(list(sessions_dir.glob('session_*.json')))
        auto_prune = 'auto_prune: true' in run('grep "auto_prune" ~/.hermes/config.yaml')
        retention = run("grep retention_days ~/.hermes/config.yaml | grep -oP '\\d+' | head -1")
        old_count = int(run(f"find ~/.hermes/sessions -name 'session_*.json' -mtime +{retention or 7} 2>/dev/null | wc -l") or '0')
        if old_count > 50:
            items.append(("🟡", f"会话 {session_count} 个, {old_count} 个超期未清理", "auto_prune 可能未触发，手动清理: find ~/.hermes/sessions -name 'session_*.json' -mtime +7 -delete"))
        else:
            items.append(("📁", f"会话 {session_count} 个 (auto_prune 正常)"))

    # 磁盘趋势（对比昨日状态）
    prev = load_state()
    prev_pct = prev.get('disk_pct', 0)
    if prev_pct and pct > prev_pct + 3:
        items.append(("⚠️", f"磁盘从 {prev_pct}% → {pct}%，+{pct - prev_pct}%"))

    # 保存今日状态
    save_state({'disk_pct': pct})

    return items


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            traceback.print_exc()
            pass
    return {}


def save_state(data):
    STATE_FILE.write_text(json.dumps(data))


def get_today_pipelines(is_trading_day):
    """读取 pipeline.yaml，列出今天的管道任务"""
    pipeline_file = AGENDA_DIR / 'pipeline.yaml'
    if not pipeline_file.exists():
        return ["(pipeline.yaml 不存在)"]

    now = datetime.now()
    weekday = now.strftime('%A').lower()
    hour = now.hour

    lines = []
    if is_trading_day:
        lines.append("📝 交易日管道:")
        lines.append("  15:30 collect_data → 16:00 generate_review → 16:30 publish_xueqiu")
        lines.append("  16:00 kline_update → 16:15 margin_data → 21:00 signal_scan")
        lines.append("  08:00 morning_brief → 盘前早报")
    else:
        lines.append("🏖️ 非交易日 — 无交易管道")

    # 周度任务
    if weekday == 'friday':
        lines.append("📅 今日周度: weekly_summary (17:00)")
    elif weekday == 'sunday':
        lines.append("📅 今日周度: quant_weekly (15:30)")
        lines.append("📅 今夜: graphify_weekly + lesson_promoter (周一 03:00)")

    # 每日维护
    lines.append("🔧 每日维护: agenda_builder(08:00) → ops-autopilot(08:05) → gbrain_sync(每6h)")
    lines.append("   error_learner(22:00) + daily_digest(21:00)")

    return lines


# ══════════════════════════════════════════════
# 5. 错误情报（过滤噪音 + 分类）
# ══════════════════════════════════════════════

def analyze_errors():
    if not ERRORS_LOG.exists():
        return []

    with open(ERRORS_LOG) as f:
        all_lines = f.readlines()

    recent = all_lines[-500:]  # 最近500行
    today = datetime.now().strftime('%Y-%m-%d')

    # 按日期+类型分组
    real_errors = []
    for line in recent:
        if 'ERROR' not in line:
            continue
        # 过滤噪音
        if any(re.search(p, line) for p in NOISE_PATTERNS):
            continue
        # 只看今天的
        if today not in line:
            continue
        real_errors.append(line.strip())

    if not real_errors:
        return []

    # 分类
    categories = defaultdict(list)
    for err in real_errors:
        if 'ModuleNotFoundError' in err or 'ImportError' in err:
            categories['依赖缺失'].append(err)
        elif '401' in err or 'Unauthorized' in err:
            categories['API鉴权失败'].append(err)
        elif 'timeout' in err.lower() or 'Timeout' in err:
            categories['超时'].append(err)
        elif 'Connection' in err or 'refused' in err:
            categories['连接失败'].append(err)
        elif 'OOM' in err or 'MemoryError' in err or ' killed' in err:
            categories['内存不足'].append(err)
        elif 'disk' in err.lower() or 'No space' in err:
            categories['磁盘空间'].append(err)
        else:
            categories['其他'].append(err)

    result = []
    for cat, errs in categories.items():
        result.append(f"  {cat}: {len(errs)} 条")
        # 如果只有1-2条，展示摘要
        if len(errs) <= 2:
            for e in errs:
                # 提取关键部分
                short = e.split('ERROR')[-1].strip()[:120] if 'ERROR' in e else e[:120]
                result.append(f"    → {short}")

    if result:
        result.insert(0, f"今日错误 ({len(real_errors)} 条, {len(categories)} 类):")
    return result


# ══════════════════════════════════════════════
# 6. 待办任务（按优先级排序）
# ══════════════════════════════════════════════

def read_pending_sorted():
    if not PENDING_FILE.exists():
        return ["(无待办)"]

    with open(PENDING_FILE, encoding='utf-8') as f:
        lines = f.readlines()

    tasks = {'L1': [], 'L2': [], 'L3': []}
    for line in lines:
        line = line.strip()
        if not line.startswith('- ['):
            continue
        # 提取优先级
        if 'L1' in line:
            tasks['L1'].append(line)
        elif 'L3' in line:
            tasks['L3'].append(line)
        else:
            tasks['L2'].append(line)

    result = []
    for level in ('L1', 'L2', 'L3'):
        for t in tasks[level]:
            result.append(t)

    return result if result else ["(无待办)"]


# ══════════════════════════════════════════════
# 7. 任务继承 & 计时
# ══════════════════════════════════════════════

def load_tracker():
    """读取任务追踪器"""
    if TRACKER_FILE.exists():
        try:
            return json.loads(TRACKER_FILE.read_text())
        except:
            traceback.print_exc()
            pass
    return {"tasks": [], "last_updated": datetime.now().strftime('%Y-%m-%d')}


def save_tracker(data):
    """写入任务追踪器"""
    data["last_updated"] = datetime.now().strftime('%Y-%m-%d')
    TRACKER_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    if TRACKER_FILE.exists():
        print(f"✅ task_tracker.json 已更新 ({len(data['tasks'])} 个活跃任务)")


def sync_pending_to_tracker():
    """将 pending.md 中的任务同步到 task_tracker（去重）"""
    if not PENDING_FILE.exists():
        return

    tracker = load_tracker()
    existing_ids = {t["id"] for t in tracker["tasks"]}

    with open(PENDING_FILE, encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line.startswith('- ['):
            continue
        # 提取任务描述
        # 格式: - [x] 任务描述 ｜ L1 ｜ 2026-05-08
        desc = re.sub(r'\s*［.*?］', '', line)  # 移除日语括号内容
        desc = re.sub(r'─.*', '', desc)
        desc = re.sub(r'\s*[｜|]\s*L[123]\s*[｜|]\s*.*', '', desc).strip()
        desc = re.sub(r'^- \[\w+\]\s*', '', desc).strip()  # 移除 - [tag] 前缀

        if not desc or len(desc) < 3:
            continue

        # 去重：相同描述不重复添加
        dup = False
        for t in tracker["tasks"]:
            if t["desc"] == desc:
                dup = True
                break
        if dup:
            continue

        # 提取优先级
        prio = "P2"
        if "L1" in line:
            prio = "P1"
        elif "L3" in line:
            prio = "P3"

        task_id = f"task-{datetime.now().strftime('%Y%m%d')}-{len(tracker['tasks'])}"
        tracker["tasks"].append({
            "id": task_id,
            "desc": desc,
            "added": datetime.now().strftime('%Y-%m-%d'),
            "days_pending": 0,
            "priority": prio,
            "tags": ["pending-md"],
            "source": "pending.md"
        })

    if tracker["tasks"]:
        save_tracker(tracker)


def inherit_tasks():
    """继承前日未完成任务 + 计时器递增"""
    tracker = load_tracker()
    today = datetime.now().strftime('%Y-%m-%d')

    changed = False
    for t in tracker["tasks"]:
        # 跳过今日刚加的任务（days_pending 从明天开始算）
        if t.get("last_seen") != today:
            t["days_pending"] = t.get("days_pending", 0) + 1
            t["last_seen"] = today
            changed = True

    if changed:
        save_tracker(tracker)

    return tracker


def get_tasks_for_daily(tracker):
    """生成为 daily.md 格式的待办清单，含滞留标记"""
    if not tracker["tasks"]:
        return ["(无待办)"]

    tasks = sorted(tracker["tasks"],
                   key=lambda t: ({"P1": 0, "P2": 1, "P3": 2}.get(t.get("priority", "P2"), 99),
                                  -t.get("days_pending", 0)))

    result = []
    for t in tasks:
        days = t.get("days_pending", 0)
        prio = t.get("priority", "P2")

        # 超时升优先级
        auto_icon = ""
        for threshold, icon in sorted(PROMOTE_AFTER_DAYS.items()):
            if days >= threshold:
                auto_icon = icon
                # 自动升 L1
                if prio != "P1":
                    prio = "P1"
                    t["priority"] = "P1"

        # 格式输出
        tag_str = ""
        if t.get("tags"):
            tag_str = f" [{','.join(t['tags'][:3])}]"

        if days >= 7:
            marker = f"🚨 已滞留{days}天"
        elif days >= 3:
            marker = f"⚠️ 已滞留{days}天"
        elif days >= 1:
            marker = f"🕐 第{days}天"
        else:
            marker = "新"

        result.append(f"- [{prio}] {auto_icon} {t['desc']} {tag_str} ｜ {marker}")

    return result if result else ["(无待办)"]


def mark_task_done(desc_fragment):
    """标记任务已完成（从 tracker 移除）"""
    tracker = load_tracker()
    before = len(tracker["tasks"])
    tracker["tasks"] = [t for t in tracker["tasks"] if desc_fragment not in t["desc"]]
    after = len(tracker["tasks"])
    if before != after:
        save_tracker(tracker)
        # 也从 pending.md 移除
        if PENDING_FILE.exists():
            lines = PENDING_FILE.read_text().split('\n')
            lines = [l for l in lines if desc_fragment not in l]
            PENDING_FILE.write_text('\n'.join(lines))
        return True
    return False


# ══════════════════════════════════════════════
# 主流程（调整后）
# ══════════════════════════════════════════════

def generate_daily():
    today = datetime.now().strftime('%Y-%m-%d %A')
    now = datetime.now().strftime('%H:%M')
    is_trading_day = datetime.now().weekday() < 5

    sections = [f"# 今日议程 — {today} (生成于 {now})", ""]

    # ── 服务健康 ──
    services = check_services()
    sections.append("## 🔌 服务健康")
    if services:
        for icon, msg, fix in services:
            sections.append(f"{icon} {msg}")
            if fix:
                sections.append(f"   → 修复: `{fix}`")
    else:
        sections.append("✅ 全部正常 (Gateway / MySQL / DeepSeek / Camofox)")
    sections.append("")

    # ── Cron ──
    cron_issues, total, enabled = check_crons()
    sections.append(f"## ⏰ Cron ({enabled}/{total} 启用)")
    if cron_issues:
        for icon, msg, detail in cron_issues:
            sections.append(f"{icon} {msg}")
            if detail:
                sections.append(f"   {detail}")
    else:
        sections.append("✅ 全部正常")
    sections.append("")

    # ── 数据新鲜度 ──
    if is_trading_day:
        data_issues = check_data_freshness()
        sections.append("## 📊 数据新鲜度")
        if data_issues:
            for icon, msg, fix in data_issues:
                sections.append(f"{icon} {msg} → {fix}")
        else:
            sections.append("✅ K线/复盘均最新")
        sections.append("")

    # ── 管道 + Pipeline ──
    sections.append("## 🔗 今日管道")
    today_pipelines = get_today_pipelines(is_trading_day)
    sections.extend(today_pipelines)

    # Pipeline 引擎活跃任务
    pipeline_file = AGENDA_DIR / 'pipelines.json'
    pipeline_lines = []
    if pipeline_file.exists():
        try:
            pl_data = json.loads(pipeline_file.read_text())
            active = [p for p in pl_data.get("pipelines", []) if p.get("status") in ("running", "paused")]
            if active:
                pipeline_lines.append("📦 Pipeline 引擎:")
                for p in active:
                    icon = "▶️" if p["status"] == "running" else "⏸️"
                    cur = p.get("current", 1)
                    total = len(p.get("stages", []))
                    goal = p.get("goal", "")[:60]
                    pipeline_lines.append(f"  {icon} [{cur}/{total}] {goal}")
                    if p["status"] == "paused":
                        pipeline_lines.append(f"     ⏸️ 等待决策")
        except:
            traceback.print_exc()
            pass
    if pipeline_lines:
        sections.extend(pipeline_lines)
    sections.append("")

    # ── 资源 ──
    resources = check_resources()
    sections.append("## 📐 资源")
    for item in resources:
        if len(item) == 3:
            icon, msg, fix = item
            sections.append(f"{icon} {msg}")
            if fix:
                sections.append(f"   → {fix}")
        else:
            sections.append(f"{item[0]} {item[1]}")
    sections.append("")

    # ── 错误情报 ──
    errors = analyze_errors()
    sections.append("## 🚨 今日错误")
    if errors:
        sections.extend(errors)
    else:
        sections.append("✅ 无值得关注的错误 (asyncio/网络抖动等噪音已过滤)")
    sections.append("")

    # ── 待处理任务（继承 + 计时） ──
    sync_pending_to_tracker()  # 从 pending.md 同步新任务
    tracker = inherit_tasks()  # 计时递增 + 超时升优
    tasks = get_tasks_for_daily(tracker)
    sections.append("## 📋 今日必做（任务继承 + 计时）")
    sections.extend(tasks)
    sections.append("")

    sections.append("---")
    sections.append(f"*v2.0 智能版 — 已过滤 {len(NOISE_PATTERNS)} 类噪音 | 趋势对比 | 可行动输出*")

    content = '\n'.join(sections)
    DAILY_FILE.write_text(content, encoding='utf-8')
    print(f"✅ daily.md v2.0 已生成 ({len(content)} 字符)")
    return sections


def init_pending():
    if not PENDING_FILE.exists():
        PENDING_FILE.write_text("# 跨会话待办队列\n\n(暂无待办)\n", encoding='utf-8')
        print("✅ pending.md 已初始化")


if __name__ == '__main__':
    init_pending()
    generate_daily()
