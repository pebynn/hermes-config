import sys, os, pymysql
sys.path.insert(0, '/home/pebynn/quant')

password = os.environ.get('MYSQL_STOCK_PASSWORD', '')
conn = pymysql.connect(host='127.0.0.1', port=3306, user='stock',
                       password=password, database='stock_kline')
c = conn.cursor()

c.execute("SELECT * FROM daily_signal_detail WHERE signal_date='2026-05-13' ORDER BY `rank`")
cols = [d[0] for d in c.description]
print(f"=== Existing details ({len(c.fetchall())} rows) ===")
c.execute("SELECT * FROM daily_signal_detail WHERE signal_date='2026-05-13' ORDER BY `rank`")
for row in c.fetchall():
    r = dict(zip(cols, row))
    print(f"  rank={r['rank']} code={r['code']} name={r['name']} industry={r['industry']} score={r['composite_score']}")

conn.close()
