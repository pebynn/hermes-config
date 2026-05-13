#!/usr/bin/env python3
"""Test MySQL connection with actual password."""
import os
import pymysql

pw = "stock123"  # from ~/.hermes/.env

try:
    c = pymysql.connect(host="127.0.0.1", user="stock", password=pw, database="stock_kline")
    cur = c.cursor()
    cur.execute("SHOW TABLES")
    tables = [t[0] for t in cur.fetchall()]
    print(f"Tables ({len(tables)}): {tables}")
    
    signal_t = [t for t in tables if 'signal' in t.lower()]
    print(f"Signal tables: {signal_t}")
    
    for st in signal_t:
        cur.execute(f"DESCRIBE {st}")
        print(f"\n{st}:")
        for r in cur.fetchall():
            print(f"  {r}")
    
    c.close()
except Exception as e:
    print(f"Error: {e}")
