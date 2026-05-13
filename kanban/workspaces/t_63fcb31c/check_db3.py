import sys, os, pymysql
sys.path.insert(0, '/home/pebynn/quant')

password = os.environ.get('MYSQL_STOCK_PASSWORD', '')
conn = pymysql.connect(host='127.0.0.1', port=3306, user='stock',
                       password=password, database='stock_kline')
c = conn.cursor()

# Check what stock 000905 actually is - look at stock files
c.execute("SELECT code, trade_date, `close`, pct_chg FROM kline WHERE code='000905' ORDER BY trade_date DESC LIMIT 2")
print("000905 data:", c.fetchall())

# Check 510500 (ZZ500 ETF)
c.execute("SELECT code, trade_date, `close`, pct_chg FROM kline WHERE code='510500' ORDER BY trade_date DESC LIMIT 2")
print("510500:", c.fetchall())

# Check what codes look like indices (check if any code has 'SH' in source or similar)
c.execute("SELECT DISTINCT source FROM kline LIMIT 10")
print("Sources:", [r[0] for r in c.fetchall()])

# Let's also check daily_signal for previous reports to see format precedent
c.execute("SELECT signal_date, total_stocks, top1_code, top1_name, top1_score, zz500_change, industry_count FROM daily_signal ORDER BY signal_date DESC LIMIT 5")
print("\n=== Previous daily_signal records ===")
for row in c.fetchall():
    print(row)

conn.close()
