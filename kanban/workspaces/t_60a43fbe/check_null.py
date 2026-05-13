#!/home/pebynn/tools/quant_env/bin/python3
import sys
sys.path.insert(0, '/home/pebynn/quant')
from data_common import _get_db_engine
from sqlalchemy import text
engine = _get_db_engine()
with engine.connect() as conn:
    r = conn.execute(text("""
        SELECT code, COUNT(*) as cnt 
        FROM kline 
        WHERE trade_date >= '2024-01-01' AND total_mv IS NULL 
        GROUP BY code 
        ORDER BY cnt DESC
    """))
    rows = r.fetchall()
    print(f'Codes with NULL total_mv: {len(rows)}')
    for row in rows:
        print(f'  {row[0]}: {row[1]} rows')
    total = sum(row[1] for row in rows)
    print(f'Total NULL rows: {total}')
engine.dispose()
