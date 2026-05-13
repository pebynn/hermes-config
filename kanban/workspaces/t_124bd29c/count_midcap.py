#!/home/pebynn/tools/quant_env/bin/python3
"""Count mid-cap stocks (50-400亿) for factor pipeline planning."""
import sys
sys.path.insert(0, '/home/pebynn/quant')
from data_common import get_stock_list, load_share_db
from pathlib import Path
import pandas as pd
import time

home = Path.home()
kline_dir = home / '.finquant' / 'cache' / 'kline'
sd = load_share_db()
sl = get_stock_list(market='all')

# Quick scan: read last kline data from parquet + multiply by shares
t0 = time.time()
valid_shares = {c: s for c, s in sd.items() if s and s > 0}
print(f"Total with valid shares: {len(valid_shares)}")

mid_cap = []
for code in sl['code'].tolist():
    shares = sd.get(code)
    if shares is None or shares <= 0:
        continue
    path = kline_dir / f'{code}.parquet'
    if not path.exists():
        continue
    try:
        tail = pd.read_parquet(path, columns=['收盘'], filters=[('日期', '>=', '2026-01-01')])
        if tail.empty:
            continue
        price = tail['收盘'].iloc[-1]
        cap = shares * price
        if 50e8 <= cap <= 400e8:
            mid_cap.append({'code': code, 'cap': cap})
    except:
        continue

print(f"Mid-cap (50-400亿, parquet only): {len(mid_cap)} stocks, {time.time()-t0:.1f}s")
if mid_cap:
    caps = [m['cap']/1e8 for m in mid_cap]
    print(f"Cap range: {min(caps):.0f}亿 - {max(caps):.0f}亿, median: {sorted(caps)[len(caps)//2]:.0f}亿")
