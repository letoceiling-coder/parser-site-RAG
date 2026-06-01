#!/bin/bash
# Findpapers — периодический поиск научных статей

cd /app

while true; do
    echo "[$(date)] Running findpapers queries..."
    python main.py || echo "findpapers run failed"
    echo "[$(date)] Sleeping 24 hours..."
    sleep 86400
done
