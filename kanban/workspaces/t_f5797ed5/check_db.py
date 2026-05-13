#!/usr/bin/env python3
"""Check MySQL tables for signal storage."""
import pymysql
c = pymysql.connect(host="127.0.0.1", user="stock", password="***", database="stock_kline")
cur = c.cursor()
cur.execute("SHOW TABLES")
tables = cur.fetchall()
print("Tables:")
for t in tables:
    print(f"  {t[0]}")

# Check if signal tables exist
signal_tables = [t[0] for t in tables if 'signal' in t[0].lower()]
if signal_tables:
    print(f"\nSignal tables found: {signal_tables}")
    for st in signal_tables:
        cur.execute(f"DESCRIBE {st}")
        print(f"\n{st} schema:")
        for row in cur.fetchall():
            print(f"  {row}")
else:
    print("\nNo signal-specific tables found")
    # List some other relevant tables
    other = [t[0] for t in tables if any(k in t[0].lower() for k in ['daily','strategy','factor'])]
    if other:
        print(f"Related tables: {other}")

c.close()
