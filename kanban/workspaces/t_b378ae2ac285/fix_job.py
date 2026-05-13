#!/usr/bin/env python3
import json

path = '/home/pebynn/.hermes/cron/jobs.json'
with open(path) as f:
    data = json.load(f)

jobs = data.get('jobs', [])
for job in jobs:
    if job.get('id') == 'afff56398abe':
        job['prompt'] = (
            '\u6267\u884c\u6bcf\u65e5K\u7ebf\u66f4\u65b0\uff0c\u8d85\u65f6600s\u3002\n\n'
            + '\u6b65\u9aa4\uff1a\n'
            + '1. \u8fd0\u884c: export HOME=/home/pebynn && cd /home/pebynn/quant && '
            + 'timeout 600 /home/pebynn/tools/quant_env/bin/python3 '
            + '/home/pebynn/quant/daily_kline_update.py\n'
            + '2. \u68c0\u67e5stderr\u8f93\u51fa\u6700\u540e5\u884c\u786e\u8ba4\u201c\u6210\u529f\u201d\u6216\u201c\u5b8c\u6210\u201d\u5b57\u6837\n'
            + '3. \u9a8c\u8bc1: python3 -c \u201cimport mysql.connector; '
            + "conn=mysql.connector.connect(host='127.0.0.1',user='stock',"
            + "password='stock888',database='stock_kline'); "
            + "c=conn.cursor(); c.execute('SELECT MAX(trade_date) FROM kline'); "
            + "print('Latest:',c.fetchone()[0]); conn.close()\u201d\n"
            + '4. \u5982\u679c\u6b65\u9aa42\u5931\u8d25\u6216\u6700\u65b0\u65e5\u671f<\u6628\u5929 \u2192 \u62a5\u544a\u5931\u8d25\u539f\u56e0\u3002\u6210\u529f\u5219\u4e0d\u51fa\u58f0\u3002'
        )
        job['no_agent'] = False
        job['script'] = None
        break

data['updated_at'] = '2026-05-13T22:00:00+08:00'
with open(path, 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('Done')
