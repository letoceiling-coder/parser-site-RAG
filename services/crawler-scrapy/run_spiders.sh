#!/bin/bash
# Scrapy scheduler — запуск пауков по расписанию из configs/sources/legal_sites.yaml

cd /app
echo "Scrapy crawler started. Spiders: $(scrapy list 2>/dev/null || echo 'loading...')"

while true; do
    for spider in pravo_gov sudact cyberleninka pravo_ru rg_ru; do
        echo "[$(date)] Running spider: $spider"
        scrapy crawl "$spider" -s LOG_LEVEL=INFO 2>&1 || echo "Spider $spider failed"
        sleep 60
    done
    echo "[$(date)] All spiders completed. Sleeping 6 hours..."
    sleep 21600
done
