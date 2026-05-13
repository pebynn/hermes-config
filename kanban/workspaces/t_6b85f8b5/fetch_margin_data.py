#!/usr/bin/env python3
"""Fetch and cache margin (两融) data for today."""
import sys
sys.path.insert(0, "/home/pebynn/quant")
from margin_data import fetch_and_cache_today
import json

result = fetch_and_cache_today()
print(result)
