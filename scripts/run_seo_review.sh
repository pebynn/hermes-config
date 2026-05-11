#!/bin/bash
# Wrapper for SEO review generation (called by cron)
cd /home/pebynn/writing-data/scripts
python3 generate_review_seo.py "$@"
