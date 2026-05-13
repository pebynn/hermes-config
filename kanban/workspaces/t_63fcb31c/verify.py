import sys, os, pymysql
sys.path.insert(0, '/home/pebynn/quant')
password = os.environ.get('MYSQL_STOCK_PASSWORD', '')
conn = pymysql.connect(host='127.0.0.1', port=3306, user='stock', password=password, database='stock_kline')
c = conn.cursor()

# Verify daily_signal update
c.execute("SELECT signal_date, total_stocks, zz500_change, LEFT(report_summary,100) AS report_preview FROM daily_signal WHERE signal_date='2026-05-13'")
print("=== daily_signal ===")
for r in c.fetchall():
    print(f"  date={r[0]} stocks={r[1]} zz500={r[2]}% preview={r[3][:80]}...")

# Verify detail scores
c.execute("SELECT code, name, l1_score, l2_score, ff_score, l3_score, buy2_price, buy2_level FROM daily_signal_detail WHERE signal_date='2026-05-13' AND `rank`<=3")
print("\n=== Top3 detail with scores ===")
for r in c.fetchall():
    print(f"  {r[0]} {r[1]}: L1={r[2]} L2={r[3]} FF={r[4]} L3={r[5]} price={r[6]} level={r[7]}")

conn.close()
