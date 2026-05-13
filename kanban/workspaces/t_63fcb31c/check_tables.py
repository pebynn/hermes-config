import mysql.connector

conn = mysql.connector.connect(host='localhost', database='stock_kline')
c = conn.cursor()
c.execute("SHOW TABLES LIKE '%signal%'")
tables = c.fetchall()
print("Signal tables:", tables)
for t in tables:
    tn = t[0]
    c.execute(f"DESCRIBE {tn}")
    print(f"\n=== {tn} ===")
    for row in c.fetchall():
        print(row)
conn.close()
