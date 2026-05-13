#!/usr/bin/env python3
import json

path = '/home/pebynn/.hermes/cron/jobs.json'
with open(path) as f:
    data = json.load(f)

jobs = data.get('jobs', [])
for job in jobs:
    if job.get('id') == 'afff56398abe':
        job['prompt'] = (
            '执行每日K线更新，超时600s。\n\n'
            '步骤：\n'
            '1. 运行: export HOME=/home/pebynn && cd /home/pebynn/quant && '
            'timeout 600 /home/pebynn/tools/quant_env/bin/python3 '
            '/home/pebynn/quant/daily_kline_update.py\n'
            '2. 检查stderr输出最后5行确认"成功"或"完成"字样\n'
            '3. 验证最新数据: python3 -c \'import mysql.connector; '
            "conn=mysql.connector.connect(host='127.0.0.1',user='stock',"
            "password='stock888',database='stock_kline'); "
            "c=conn.cursor(); c.execute('SELECT MAX(trade_date) FROM kline'); "
            "print('Latest:',c.fetchone()[0]); conn.close()'\n"
            '4. 如果步骤2失败或最新日期<昨天 → 报告失败原因。成功则不出声。'
        )
        job['no_agent'] = False
        job['script'] = None
        break

data['updated_at'] = '2026-05-13T22:05:00+08:00'
with open(path, 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('Done')
