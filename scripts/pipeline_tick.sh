#!/bin/bash
# pipeline_tick.sh — wrapper for cron no_agent mode
cd "$HOME" && python3 "$HOME/.hermes/scripts/pipeline_runner.py" tick
