import sys, os, pymysql
sys.path.insert(0, '/home/pebynn/quant')
password = os.environ.get('MYSQL_STOCK_PASSWORD', '')
conn = pymysql.connect(host='127.0.0.1', port=3306, user='stock', password=password, database='stock_kline')
c = conn.cursor()

c.execute("SELECT LENGTH(report_summary) FROM daily_signal WHERE signal_date='2026-05-13'")
length = c.fetchone()[0]
c.execute("SELECT report_summary FROM daily_signal WHERE signal_date='2026-05-13'")
summary = c.fetchone()[0]
print(f"report_summary length: {length} chars")
print(f"--- last 200 chars ---")
print(summary[-200:])

# Also verify detail scores fully populated (none should be NULL)
c.execute("SELECT COUNT(*) FROM daily_signal_detail WHERE signal_date='2026-05-13' AND l1_score IS NULL")
nulls = c.fetchone()[0]
print(f"\nDetail records with NULL l1_score: {nulls}")

# Check bus file
bus_path = os.path.expanduser('~/.hermes/bus/quant-signal-to-writer/2026-05-13.json')
print(f"\nBus file exists: {os.path.exists(bus_path)}")
print(f"Bus file size: {os.path.getsize(bus_path)} bytes")

conn.close()
