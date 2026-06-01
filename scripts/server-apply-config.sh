#!/bin/bash
set -euo pipefail
cd /opt/parser-site-rag
git pull
sed -i 's/\r$//' scripts/*.sh 2>/dev/null || true

export S3_SECRET_KEY=17e761b1659d43aa85edbc3bad2a7785
export CAPTCHA_API_KEY=c95532f35467ecf9c46bfddcb7e40db7
export PROXY_ENABLED=true
bash scripts/update-secrets.sh

docker compose up -d --build proxy-rotator crawler-crawl4ai crawler-scrapy celery-worker api-gateway findpapers 2>&1 | tail -5

echo "--- S3 test ---"
docker compose run --rm --no-deps api-gateway python3 -c "
import boto3, os
c = boto3.client('s3',
    endpoint_url=os.environ.get('S3_ENDPOINT'),
    region_name=os.environ.get('S3_REGION','ru-3'),
    aws_access_key_id=os.environ.get('S3_ACCESS_KEY'),
    aws_secret_access_key=os.environ.get('S3_SECRET_KEY'))
try:
    c.head_bucket(Bucket=os.environ.get('S3_BUCKET','knowledge-raw'))
    print('S3 OK: bucket accessible')
except Exception as e:
    print('S3 ERROR:', e)
" 2>&1 || echo "S3 test skipped"

echo "--- 2captcha test ---"
curl -s "https://2captcha.com/res.php?key=${CAPTCHA_API_KEY}&action=getbalance" | head -c 50
echo

echo "--- Proxy rotator ---"
sleep 15
docker logs parser-proxy-rotator 2>&1 | tail -3
cat /var/lib/docker/volumes/parser-site-rag_crawl4ai_data/_data/proxies.json 2>/dev/null | head -c 200 || docker exec parser-proxy-rotator cat /data/proxies.json 2>/dev/null | head -c 200 || echo "proxies pending"

echo "Done"
