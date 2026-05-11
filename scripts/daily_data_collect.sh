#!/bin/bash
# 每日数据采集+图表生成 — 15:30 触发
# 被 Writing kanban 管线依赖，必须在 kanban 之前完成

cd /home/pebynn/writing-data/scripts || exit 1
python3 data_collector_seo.py 2>&1
python3 generate_charts.py 2>&1
echo "data_collection_done: $(date +%F_%T)"
