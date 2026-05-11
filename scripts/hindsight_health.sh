#!/bin/bash
# hindsight health check — 每30min检测，挂了自动拉起
if ! curl -s http://localhost:8888/health | grep -q healthy; then
    echo "[$(date)] hindsight down, restarting..."
    cd ~/tools/hindsight && docker compose up -d
    # 等30s让模型加载
    sleep 30
    ~/tools/hindsight/ensure_hindsight.sh
fi
