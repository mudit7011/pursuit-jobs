#!/bin/bash
cd /Users/muditchaudhary/job-autopilot
source .env 2>/dev/null || true

while true; do
    echo "[$(date)] Starting bot..." >> logs/run.log
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m src.main >> logs/run.log 2>&1
    echo "[$(date)] Bot crashed or stopped, restarting in 5s..." >> logs/run.log
    sleep 5
done
