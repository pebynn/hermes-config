#!/home/pebynn/tools/quant_env/bin/python3
"""
P4 推送QQBot — 格式化信号日报 + 写入MySQL + 通知
消费 /tmp/midcap_signal.json 输出
"""
import json, os, sys
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, '/home/pebynn/quant')
import pymysql

# ── 1. 读取信号 ──
with open('/tmp/midcap_signal.json') as f:
    data = json.load(f)

top20 = data['top20']
date_str = data['date']

# ── 2. 计算行业分布（前10 + 全部）──
industry_counts = {}
for s in top20:
    ind = s['industry']
    industry_counts[ind] = industry_counts.get(ind, 0) + 1
industry_sorted = sorted(industry_counts.items(), key=lambda x: -x[1])

# ── 3. 格式化日报文本 ──
lines = []
lines.append(f"🔔 量化信号日报 | {date_str}")
lines.append(f"┄" * 30)
lines.append(f"中盘标的池: {data['total_screened']}只 | 覆盖行业: {data['total_industries']}个")
lines.append(f"权重: L1×0.25 + L2×0.30 + FF×0.20 + L3×0.25")
lines.append(f"")

# Top10
lines.append(f"📋 TOP10 信号")
lines.append(f"┄" * 30)
for s in top20[:10]:
    rank = s['rank']
    name = s['name']
    code = s['code']
    ind = s['industry']
    score = s['neutralized_score']
    comp = s['components']
    # Score bar visual
    bar_len = int(score * 30)
    bar = "█" * bar_len + "░" * (30 - bar_len)
    lines.append(f"#{rank:2d} {name}({code}) [{ind}]")
    lines.append(f"   总分 {score:.4f} {bar}")
    lines.append(f"   L1={comp['L1_pct']:.1f} L2={comp['L2_pct']:.1f} FF={comp['FF_pct']:.1f} L3={comp['L3_pct']:.1f}")

# Industry distribution
lines.append(f"")
lines.append(f"📊 行业分布 (Top20)")
lines.append(f"┄" * 30)
for ind, cnt in industry_sorted:
    bar_i = "▓" * cnt + "░" * (6 - cnt)
    lines.append(f"  {ind:10s} {bar_i} {cnt}只")

# Summary
lines.append(f"")
lines.append(f"📈 信号摘要")
lines.append(f"┄" * 30)
lines.append(f"  Top1: {top20[0]['name']}({top20[0]['code']})  score={top20[0]['neutralized_score']:.4f}")
lines.append(f"  Top3: {top20[2]['name']}({top20[2]['code']})  score={top20[2]['neutralized_score']:.4f}")
lines.append(f"  score range: {top20[-1]['neutralized_score']:.4f} ~ {top20[0]['neutralized_score']:.4f}")
lines.append(f"  行业集中度: Top行业{industry_sorted[0][0]}({industry_sorted[0][1]}只)")

lines.append(f"")
lines.append(f"⚡ 由P3信号扫描管线生成 | 仅供参考，不构成投资建议")

report_text = "\n".join(lines)

# ── 4. 连接MySQL ──
password = os.environ.get('MYSQL_STOCK_PASSWORD', '')
conn = pymysql.connect(host='127.0.0.1', port=3306, user='stock',
                       password=password, database='stock_kline')
c = conn.cursor()

# ── 5. 获取zz500_change ──
c.execute("SELECT pct_chg FROM kline WHERE code='000905' AND trade_date=%s", (date_str,))
zz_row = c.fetchone()
zz500_chg = float(zz_row[0]) if zz_row else None
print(f"zz500_change: {zz500_chg}%")

# ── 6. 更新 daily_signal ──
report_short = (
    f"中盘{len(top20)}只信号, "
    f"Top1:{top20[0]['name']}({top20[0]['code']}) score={top20[0]['neutralized_score']:.4f}, "
    f"中证500={zz500_chg:+.2f}%" if zz500_chg else ""
)
c.execute("""
    UPDATE daily_signal
    SET zz500_change=%s, report_summary=%s
    WHERE signal_date=%s
""", (zz500_chg, report_text, date_str))
print(f"daily_signal updated: {c.rowcount} rows")

# ── 7. 更新 daily_signal_detail (填充分项得分) ──
for s in top20:
    code = s['code']
    rank = s['rank']
    comp = s['components']

    # Determine buy2_level based on the buy2_score
    raw = s.get('raw_data', {})
    buy2_score = raw.get('buy2_score', 0)
    if buy2_score >= 90:
        buy2_level = 'A'
    elif buy2_score >= 75:
        buy2_level = 'B'
    else:
        buy2_level = 'C'

    c.execute("""
        UPDATE daily_signal_detail
        SET l1_score=%s, l2_score=%s, ff_score=%s, l3_score=%s,
            l1_adj=%s, l2_adj=%s, ff_adj=%s, l3_adj=%s,
            buy2_price=%s, buy2_level=%s
        WHERE signal_date=%s AND code=%s
    """, (
        Decimal(str(comp['L1_pct'])),
        Decimal(str(comp['L2_pct'])),
        Decimal(str(comp['FF_pct'])),
        Decimal(str(comp['L3_pct'])),
        Decimal(str(comp['L1_pct'])),
        Decimal(str(comp['L2_pct'])),
        Decimal(str(comp['FF_pct'])),
        Decimal(str(comp['L3_pct'])),
        Decimal(str(raw.get('buy2_price', 0))),
        buy2_level,
        date_str,
        code,
    ))
    if c.rowcount == 0:
        # No existing row — insert
        c.execute("""
            INSERT INTO daily_signal_detail
            (signal_date, `rank`, code, name, industry, composite_score,
             l1_score, l2_score, ff_score, l3_score,
             l1_adj, l2_adj, ff_adj, l3_adj,
             buy2_price, buy2_level)
            VALUES (%s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s)
        """, (
            date_str, rank, code, s['name'], s['industry'],
            Decimal(str(s['neutralized_score'])),
            Decimal(str(comp['L1_pct'])),
            Decimal(str(comp['L2_pct'])),
            Decimal(str(comp['FF_pct'])),
            Decimal(str(comp['L3_pct'])),
            Decimal(str(comp['L1_pct'])),
            Decimal(str(comp['L2_pct'])),
            Decimal(str(comp['FF_pct'])),
            Decimal(str(comp['L3_pct'])),
            Decimal(str(raw.get('buy2_price', 0))),
            buy2_level,
        ))

conn.commit()
print(f"detail records updated/inserted for {len(top20)} stocks")

conn.close()

# ── 8. 发送QQ Bot通知 ──
# Use Python API to notify.py (supports priority param)
sys.path.insert(0, os.path.expanduser('~/.hermes/scripts'))
from notify import send

# Short notification body (Trim if over limit)
notify_body = (
    f"📊 {date_str} 量化信号日报\n"
    f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
    f"筛选: {data['total_screened']}只中盘 | Top20覆盖{len(industry_sorted)}个行业\n"
    f"中证500: {zz500_chg:+.2f}%\n\n"
    f"🏆 Top3:\n"
    f"  #1 {top20[0]['name']}({top20[0]['code']}) {top20[0]['neutralized_score']:.4f}\n"
    f"  #2 {top20[1]['name']}({top20[1]['code']}) {top20[1]['neutralized_score']:.4f}\n"
    f"  #3 {top20[2]['name']}({top20[2]['code']}) {top20[2]['neutralized_score']:.4f}\n\n"
    f"📊 行业分布Top3:\n"
)
for ind, cnt in industry_sorted[:3]:
    notify_body += f"  {ind}: {cnt}只\n"
notify_body += f"\n📈 score区间: {top20[-1]['neutralized_score']:.4f} ~ {top20[0]['neutralized_score']:.4f}\n"
notify_body += f"🔍 查看完整日报 → daily_signal表"

ok = send("量化信号日报", notify_body, priority="P1")
print(f"QQ通知发送: {'✅ OK' if ok else '❌ FAIL'}")

# ── 9. 写入数据总线 (quant-signal-to-writer) ──
bus_dir = os.path.expanduser("~/.hermes/bus/quant-signal-to-writer")
os.makedirs(bus_dir, exist_ok=True)
bus_path = os.path.join(bus_dir, f"{date_str}.json")
bus_data = {
    "date": date_str,
    "pipeline": "P4-推送QQBot",
    "zz500_change": zz500_chg,
    "top3": [
        {"code": top20[0]['code'], "name": top20[0]['name'], "rank": 1, "score": top20[0]['neutralized_score']},
        {"code": top20[1]['code'], "name": top20[1]['name'], "rank": 2, "score": top20[1]['neutralized_score']},
        {"code": top20[2]['code'], "name": top20[2]['name'], "rank": 3, "score": top20[2]['neutralized_score']},
    ],
    "total_stocks": data['total_screened'],
    "industry_coverage": len(industry_sorted),
    "notify_sent": ok,
}
with open(bus_path, 'w') as f:
    json.dump(bus_data, f, ensure_ascii=False, indent=2)
print(f"数据总线写入: {bus_path}")

print("\n✅ P4 推送完成")
