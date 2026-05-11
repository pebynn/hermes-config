#!/bin/bash
# Wrapper for 小绿书 generation (called by cron)
cd /home/pebynn/writing-data/scripts
python3 generate_short_posts.py "$@"
