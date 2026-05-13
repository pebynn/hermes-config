#!/usr/bin/env python3
"""
量化信号日报管线 — P4: 格式化 + 推送QQ + 写入MySQL
日期: 2026-05-13

读取 /tmp/midcap_signal.json (P3输出格式) → Top10 + 分项得分 + 行业分布 → QQ Bot → MySQL
"""
import json
import os
import sys
import subprocess
import pymysql
from datetime import date, datetime
from collections import Counter

# ── 配置 ──
SIGNAL_PATH = "/tmp/midcap_signal.json"
NOTIFY_SCRIPT = os.path.expanduser("~/.hermes/scripts/notify.py")
MYSQL_PW = "stock123"
TODAY = "2026-05-13"


def load_signals():
    with open(SIGNAL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def format_daily_report(data):
    """格式化QQ日报文本"""
    date_str = data["date"]
    top20 = data.get("top20", [])
    weights = data.get("weights", {})
    total = data.get("total_screened", 0)
    total_ind = data.get("total_industries", 0)

    # Top 10
    top10 = top20[:10]

    # Industry distribution from top20
    ind_list = [s.get("industry", "") for s in top20]
    ind_counter = Counter(ind_list)
    top_ind = ind_counter.most_common(10)

    lines = []
    lines.append(f"📊 量化信号日报 {date_str}")
    lines.append(f"{'─' * 30}")

    # 概况
    lines.append("")
    lines.append(f"📋 扫描概况")
    lines.append(f"  中盘筛选: {total}只信号 (50亿~400亿)")
    lines.append(f"  涉及行业: {total_ind}个")
    lines.append(f"  权重配比: L1={weights.get('L1',0.25)}, L2={weights.get('L2',0.3)}, FF={weights.get('FF',0.2)}, L3={weights.get('L3',0.25)}")

    # ── Top 10 ──
    lines.append("")
    lines.append(f"🏆 Top 10 信号")
    lines.append("")

    for i, s in enumerate(top10):
        rank = s["rank"]
        name = s["name"]
        code = s["code"]
        ind = s.get("industry", "")
        score = s.get("neutralized_score", 0)
        comp = s.get("components", {})

        l1_pct = comp.get("L1_pct", 0)
        l2_pct = comp.get("L2_pct", 0)
        ff_pct = comp.get("FF_pct", 0)
        l3_pct = comp.get("L3_pct", 0)

        # Determine if strong buy2 signal
        raw = s.get("raw_data", {})
        buy2 = raw.get("buy2_score", 0)
        l2_tag = "🔥" if buy2 and buy2 >= 90 else ("✨" if buy2 and buy2 >= 75 else "")

        lines.append(f"  {rank}. {name} ({code})  [{ind}]")
        lines.append(f"     📈 综合={score*100:.1f}/100  {l2_tag}")
        lines.append(f"     L1={l1_pct:.0f}%│L2={l2_pct:.0f}%│FF={ff_pct:.0f}%│L3={l3_pct:.0f}%")

    # 空行
    lines.append("")

    # ── 行业分布 ──
    lines.append(f"📂 Top20 行业分布")
    lines.append("")
    for ind, cnt in top_ind:
        bar = "█" * cnt
        lines.append(f"  {ind}: {cnt}只 {bar}")

    lines.append("")
    lines.append(f"{'─' * 30}")
    lines.append(f"⚠️ 不构成投资建议 · 量化信号仅供参考")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    return "\n".join(lines)


def send_to_qq(message):
    """通过notify.py推送QQ Bot"""
    title = f"量化信号日报 {TODAY}"
    try:
        result = subprocess.run(
            ["python3", NOTIFY_SCRIPT, title, message],
            capture_output=True, text=True, timeout=15
        )
        print(f"[QQ] notify.py: {result.stdout.strip()}")
        if result.returncode != 0:
            print(f"[QQ] stderr: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"[QQ] 推送失败: {e}")
        return False


def write_to_mysql(data):
    """写入MySQL daily_signal + daily_signal_detail"""
    try:
        conn = pymysql.connect(
            host="127.0.0.1", user="stock", password=MYSQL_PW,
            database="stock_kline", charset="utf8mb4"
        )
        cur = conn.cursor()

        top20 = data.get("top20", [])

        # ── 1. daily_signal (汇总) ──
        top1 = top20[0] if top20 else {}
        top1_name = top1.get("name", "")
        top1_code = top1.get("code", "")
        top1_score = top1.get("neutralized_score", 0)

        ind_list = [s.get("industry", "") for s in top20]
        industry_count = len(set(ind_list))

        report_summary = (
            f"中盘{len(top20)}只信号, "
            f"Top1:{top1_name}({top1_code}) score={top1_score*100:.1f}"
        )

        sql_summary = """INSERT INTO daily_signal 
            (signal_date, total_stocks, top1_code, top1_name, top1_score,
             signal_count, industry_count, report_summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                total_stocks=VALUES(total_stocks),
                top1_code=VALUES(top1_code),
                top1_name=VALUES(top1_name),
                top1_score=VALUES(top1_score),
                signal_count=VALUES(signal_count),
                industry_count=VALUES(industry_count),
                report_summary=VALUES(report_summary)
        """
        cur.execute(sql_summary, (
            TODAY,
            data.get("total_screened", 0),
            top1_code,
            top1_name,
            top1_score,
            len(top20),
            industry_count,
            report_summary,
        ))
        print(f"[MySQL] daily_signal 写入成功 (id={cur.lastrowid})")

        # ── 2. daily_signal_detail (明细) ──
        cur.execute("DELETE FROM daily_signal_detail WHERE signal_date = %s", (TODAY,))

        sql_detail = """INSERT INTO daily_signal_detail
            (signal_date, `rank`, code, name, industry, 
             composite_score, l1_score, l2_score, ff_score, l3_score,
             l1_adj, l2_adj, ff_adj, l3_adj,
             buy2_date, buy2_price, buy2_level, market)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        batch = []
        weights = data.get("weights", {})

        for s in top20:
            comp = s.get("components", {})
            raw = s.get("raw_data", {})

            # Component scores as percentiles (0-100)
            l1_adj = comp.get("L1_pct", 0)
            l2_adj = comp.get("L2_pct", 0)
            ff_adj = comp.get("FF_pct", 0)
            l3_adj = comp.get("L3_pct", 0)

            # Raw factor values
            l1_total = raw.get("l1_total", 0)
            buy2_score = raw.get("buy2_score", 0)
            ff_score = raw.get("ff_score", 0)
            l3_total = raw.get("l3_total", 0)

            buy2_date = raw.get("buy2_date", None)
            buy2_price = raw.get("buy2_price", None)
            buy2_level = raw.get("buy2_level", None)

            batch.append((
                TODAY,
                s["rank"],
                s["code"],
                s["name"],
                s.get("industry", ""),
                s.get("neutralized_score", 0),
                l1_total,
                buy2_score,
                ff_score,
                l3_total,
                l1_adj,
                l2_adj,
                ff_adj,
                l3_adj,
                buy2_date,
                buy2_price,
                buy2_level,
                None,  # market
            ))

        cur.executemany(sql_detail, batch)
        conn.commit()
        print(f"[MySQL] daily_signal_detail 写入 {len(batch)} 条")

        conn.close()
        return True

    except Exception as e:
        print(f"[MySQL] 写入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ── 主流程 ──
if __name__ == "__main__":
    print(f"📊 量化信号日报管线 — {TODAY}")
    print("=" * 40)

    # 1. 加载
    print("\n[1/4] 加载信号文件...")
    data = load_signals()
    top20 = data.get("top20", [])
    top1 = top20[0] if top20 else {}
    print(f"  Top1: {top1.get('name','')}({top1.get('code','')}) score={top1.get('neutralized_score',0)*100:.1f}")
    print(f"  信号数: {len(top20)}只")

    # 2. 格式化
    print("\n[2/4] 格式化日报文本...")
    report = format_daily_report(data)
    print(report)

    # Print to stderr for logging
    print(report, file=sys.stderr, flush=True)

    # 3. 推送QQ
    print("\n[3/4] 推送QQ Bot...")
    ok = send_to_qq(report)
    print(f"  QQ推送: {'✅ 成功' if ok else '❌ 失败'}")

    # 4. 写入MySQL
    print("\n[4/4] 写入MySQL...")
    ok2 = write_to_mysql(data)
    print(f"  MySQL: {'✅ 成功' if ok2 else '❌ 失败'}")

    print("\n" + "=" * 40)
    if ok and ok2:
        print("管线完成 ✅")
    else:
        print("管线完成 ⚠️ (部分失败)")
