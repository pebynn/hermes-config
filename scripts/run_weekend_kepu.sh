#!/bin/bash
# 周末科普生成+推送
# 用法: run_weekend_kepu.sh <topic_key>
#   topic_key: k线/基金定投/主力资金/市盈率/涨停/新手亏钱/追涨

set -e
cd /home/pebynn/writing-data/scripts

# 加载环境变量
[ -f ~/.hermes/.env ] && source ~/.hermes/.env

TOPIC="${1:-k线}"
DATE=$(date +%F)

echo "[$(date)] 周末科普: topic=$TOPIC date=$DATE"
python3 generate_popular.py --topic "$TOPIC" --date "$DATE"
echo "[$(date)] 完成"
