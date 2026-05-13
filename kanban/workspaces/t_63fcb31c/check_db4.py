import sys, os, pymysql
sys.path.insert(0, '/home/pebynn/quant')

password = os.environ.get('MYSQL_STOCK_PASSWORD', '')
conn = pymysql.connect(host='127.0.0.1', port=3306, user='stock',
                       password=password, database='stock_kline')
c = conn.cursor()

# Full existing record for today
c.execute("SELECT * FROM daily_signal WHERE signal_date='2026-05-13'")
cols = [d[0] for d in c.description]
row = c.fetchone()
if row:
    print("=== Existing daily_signal for today ===")
    for i, col in enumerate(cols):
        print(f"  {col}: {row[i]}")

# Check if detail records exist for today
c.execute("SELECT COUNT(*) FROM daily_signal_detail WHERE signal_date='2026-05-13'")
cnt = c.fetchone()[0]
print(f"\nExisting detail records for today: {cnt}")

# Check what zz500 index data is available from stock index-related codes
# Actually, let me check what stocks are listed as 0009xx
c.execute("SELECT code FROM kline WHERE code LIKE '0009%' AND trade_date='2026-05-13' GROUP BY code ORDER BY code LIMIT 10")
print("\n0009xx codes:", [r[0] for r in c.fetchall()])

# Check if zz500_change for May 11 (-0.61) matches 000905 data for May 11
c.execute("SELECT trade_date, `close`, pct_chg FROM kline WHERE code='000905' AND trade_date >= '2026-05-11' ORDER BY trade_date")
print("\n000905 data for May 11-13:")
for r in c.fetchall():
    print(f"  {r[0]}: close={r[1]}, pct_chg={r[2]}%")

conn.close()
