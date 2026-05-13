import sys, os, pymysql
sys.path.insert(0, '/home/pebynn/quant')

# Try to read password from wherever it's stored
# data_common uses env var
password = os.environ.get('MYSQL_STOCK_PASSWORD', '')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='stock',
                       password=password, database='stock_kline')
c = conn.cursor()
c.execute("SELECT MAX(trade_date) FROM kline")
print('Latest date in kline:', c.fetchone())

# Check what index data we might have or codes that look like indices
c.execute("SELECT DISTINCT LEFT(code, 6) AS prefix FROM kline WHERE code LIKE '0009%' LIMIT 5")
print('Codes starting with 0009:', [r[0] for r in c.fetchall()])

c.execute("SELECT code, name, close, pct_chg FROM kline WHERE code IN ('000905','000906','510500') AND trade_date='2026-05-13'")
print('Index data for today:', c.fetchall())

c.execute("SELECT code, name, close, pct_chg FROM kline WHERE code IN ('000905','000906','510500') ORDER BY trade_date DESC LIMIT 5")
print('Recent index rows:', c.fetchall())

c.execute("SELECT DISTINCT code FROM kline WHERE code LIKE '0009%' OR code LIKE '5105%' OR code LIKE '0003%' LIMIT 20")
print('Index-like codes:', [r[0] for r in c.fetchall()])

conn.close()
