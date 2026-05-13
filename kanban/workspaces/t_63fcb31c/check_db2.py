import sys, os, pymysql
sys.path.insert(0, '/home/pebynn/quant')

password = os.environ.get('MYSQL_STOCK_PASSWORD', '')
conn = pymysql.connect(host='127.0.0.1', port=3306, user='stock',
                       password=password, database='stock_kline')
c = conn.cursor()

# Describe kline
c.execute("DESCRIBE kline")
print("=== kline schema ===")
for row in c.fetchall():
    print(row)

# Check 000905 (zz500 index code)
c.execute("SELECT code, trade_date, `close`, pct_chg FROM kline WHERE code='000905' ORDER BY trade_date DESC LIMIT 3")
print("\n=== 000905 ===")
for row in c.fetchall():
    print(row)

# Also try other index codes
for idx in ['000905','000906','000300','510500','510050']:
    c.execute(f"SELECT code, trade_date, `close`, pct_chg FROM kline WHERE code='{idx}' ORDER BY trade_date DESC LIMIT 2")
    rows = c.fetchall()
    if rows:
        print(f"\n=== {idx} ===")
        for row in rows:
            print(row)

# Latest trade date
c.execute("SELECT MAX(trade_date) FROM kline")
print(f"\nLatest date in kline: {c.fetchone()[0]}")

# Count stocks per date
c.execute("SELECT trade_date, COUNT(DISTINCT code) FROM kline GROUP BY trade_date ORDER BY trade_date DESC LIMIT 3")
print("\nRecent date counts:")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]} stocks")

conn.close()
