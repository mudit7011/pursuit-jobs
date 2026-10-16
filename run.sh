#!/bin/bash
# Keeps the bot running: restarts it a few seconds after it exits or crashes.
cd "$(dirname "$0")"
source .env 2>/dev/null || true
PYTHON="${PYTHON:-python3}"
mkdir -p logs

while true; do
    echo "[$(date)] Starting bot..." >> logs/run.log
    "$PYTHON" -m src.main >> logs/run.log 2>&1
    echo "[$(date)] Bot crashed or stopped, restarting in 5s..." >> logs/run.log
    sleep 5
done
