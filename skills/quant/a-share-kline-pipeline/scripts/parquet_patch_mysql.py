#!/home/pebynn/tools/quant_env/bin/python3
"""
parquet→MySQL pct_chg 补丁脚本 (高速版)

当 stock_kline.kline 表的 pct_chg/change 为 NULL 时，
从 parquet 缓存文件的"涨跌幅"/"涨跌额"列补全。

策略: LOAD DATA INFILE → 临时表 → UPDATE JOIN（比 executemany 快 10x）

前置条件:
  sudo mysql -e "SET GLOBAL local_infile=1"   # 开启 LOAD DATA LOCAL INFILE

用法:
  ~/tools/quant_env/bin/python3 parquet_patch_mysql.py

步数:
  1. 读取所有 parquet 缓存 → 写入 CSV
  2. LOAD DATA INFILE → 临时表 _tmp_patch
  3. UPDATE JOIN WHERE pct_chg IS NULL
  4. DROP 临时表
"""
import pymysql
from pathlib import Path
import pandas as pd
import re, sys, time, os

HOME = Path.home()
KLINE_DIR = HOME / '.finquant' / 'cache' / 'kline'
DB = {'host': '127.0.0.1', 'user': 'stock', 'password': 'stock123',
      'database': 'stock_kline', 'charset': 'utf8mb4', 'local_infile': True}

def main():
    conn = pymysql.connect(**DB)
    cur = conn.cursor()
    t0 = time.time()
    
    code_re = re.compile(r'^(\d{6})\.parquet$')
    parquet_files = sorted([f for f in KLINE_DIR.iterdir() if code_re.match(f.name)])
    print(f'parquet: {len(parquet_files)} files', flush=True)
    
    # 1. 创建临时表
    cur.execute("DROP TABLE IF EXISTS _tmp_patch")
    cur.execute("""CREATE TABLE _tmp_patch (
        code VARCHAR(10) NOT NULL,
        trade_date DATE NOT NULL,
        pct_chg DECIMAL(10,2) DEFAULT NULL,
        `change` DECIMAL(10,2) DEFAULT NULL,
        PRIMARY KEY (code, trade_date)
    ) ENGINE=InnoDB""")
    conn.commit()
    print('临时表已建', flush=True)
    
    # 2. 遍历 parquet → CSV（跳过已存在的）
    csv_path = '/tmp/_patch_data.csv'
    if os.path.exists(csv_path):
        sz = os.path.getsize(csv_path) // 1024 // 1024
        lines = sum(1 for _ in open(csv_path))
        print(f'CSV 已存在: {lines} 行, {sz}MB, 跳过生成', flush=True)
    else:
        lines = 0
        with open(csv_path, 'w') as f:
            for fi, pf in enumerate(parquet_files):
                code = code_re.match(pf.name).group(1)
                try:
                    df = pd.read_parquet(pf)
                    if df.empty or '日期' not in df.columns: continue
                    has_pct, has_chg = '涨跌幅' in df.columns, '涨跌额' in df.columns
                    if not has_pct and not has_chg: continue
                    
                    for _, row in df.iterrows():
                        tdate = str(row.get('日期', ''))
                        if not tdate: continue
                        pct = row.get('涨跌幅')
                        chg = row.get('涨跌额')
                        pct_s = f'{pct:.2f}' if pd.notna(pct) and pct != 0 else '\\N'
                        chg_s = f'{chg:.4f}' if pd.notna(chg) and chg != 0 else '\\N'
                        f.write(f'{code}\t{tdate}\t{pct_s}\t{chg_s}\n')
                        lines += 1
                except Exception as e:
                    print(f'  ERR {code}: {e}', flush=True)
                
                if (fi + 1) % 500 == 0:
                    print(f'  解析: {fi+1}/{len(parquet_files)} files, {lines} lines', flush=True)
        
        print(f'写入 {lines} 行到 CSV', flush=True)
    
    # 3. LOAD DATA INFILE
    cur.execute("TRUNCATE TABLE _tmp_patch")
    sql = f"LOAD DATA LOCAL INFILE '{csv_path}' INTO TABLE _tmp_patch (code, trade_date, pct_chg, `change`)"
    cur.execute(sql)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM _tmp_patch")
    (loaded,) = cur.fetchone()
    print(f'LOAD DATA: {loaded} 行', flush=True)
    
    # 4. UPDATE JOIN
    cur.execute("""UPDATE kline t 
        JOIN _tmp_patch s ON t.code = s.code AND t.trade_date = s.trade_date
        SET t.pct_chg = COALESCE(s.pct_chg, t.pct_chg),
            t.`change` = COALESCE(s.`change`, t.`change`)
        WHERE t.pct_chg IS NULL""")
    conn.commit()
    updated = cur.rowcount
    print(f'UPDATE JOIN: {updated} 行', flush=True)
    
    # 5. 清理
    cur.execute("DROP TABLE _tmp_patch")
    
    # 统计
    cur.execute("SELECT COUNT(*) FROM kline WHERE pct_chg IS NOT NULL")
    (filled,) = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM kline")
    (total,) = cur.fetchone()
    elapsed = (time.time() - t0) / 60
    print(f'\n完成: {elapsed:.1f}min', flush=True)
    print(f'pct_chg 覆盖率: {filled}/{total} ({filled/total*100:.1f}%)', flush=True)
    conn.close()

if __name__ == '__main__':
    main()
