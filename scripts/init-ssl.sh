#!/bin/bash
set -euo pipefail

DOMAIN="${DOMAIN:-siteaacess.ru}"
EMAIL="${SSL_EMAIL:-admin@$DOMAIN}"
PROJECT_DIR="${PROJECT_DIR:-/opt/parser-site-rag}"

SUBDOMAINS=(
    "$DOMAIN"
    "www.$DOMAIN"
    "api.$DOMAIN"
    "rag.$DOMAIN"
    "dify.$DOMAIN"
    "crawl.$DOMAIN"
    "grafana.$DOMAIN"
)

echo "=== SSL setup for $DOMAIN ==="

# Остановить nginx для standalone certbot
docker compose -f "$PROJECT_DIR/docker-compose.yml" stop nginx 2>/dev/null || true

DOMAIN_ARGS=""
for sub in "${SUBDOMAINS[@]}"; do
    DOMAIN_ARGS="$DOMAIN_ARGS -d $sub"
done

certbot certonly --standalone --non-interactive --agree-tos \
    --email "$EMAIL" \
    $DOMAIN_ARGS

# HTTPS nginx config
cat > "$PROJECT_DIR/nginx/conf.d/ssl.conf" << 'NGINX_EOF'
# Auto-generated SSL config
map $scheme $redirect_to_https {
    default 0;
    http 1;
}

server {
    listen 443 ssl http2;
    server_name siteaacess.ru www.siteaacess.ru;

    ssl_certificate /etc/letsencrypt/live/siteaacess.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/siteaacess.ru/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        root /usr/share/nginx/html;
        index index.html;
    }
}

server {
    listen 443 ssl http2;
    server_name api.siteaacess.ru;

    ssl_certificate /etc/letsencrypt/live/siteaacess.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/siteaacess.ru/privkey.pem;

    location / {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }
}

server {
    listen 443 ssl http2;
    server_name crawl.siteaacess.ru;

    ssl_certificate /etc/letsencrypt/live/siteaacess.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/siteaacess.ru/privkey.pem;

    location / {
        proxy_pass http://crawl4ai_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }
}

server {
    listen 443 ssl http2;
    server_name rag.siteaacess.ru;

    ssl_certificate /etc/letsencrypt/live/siteaacess.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/siteaacess.ru/privkey.pem;

    location / {
        proxy_pass http://host.docker.internal:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }
}

server {
    listen 443 ssl http2;
    server_name dify.siteaacess.ru;

    ssl_certificate /etc/letsencrypt/live/siteaacess.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/siteaacess.ru/privkey.pem;

    location / {
        proxy_pass http://host.docker.internal:8081;
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
        proxy_buffering off;
    }
}

server {
    listen 443 ssl http2;
    server_name grafana.siteaacess.ru;

    ssl_certificate /etc/letsencrypt/live/siteaacess.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/siteaacess.ru/privkey.pem;

    location / {
        proxy_pass http://grafana_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
    }
}
NGINX_EOF

# Redirect HTTP -> HTTPS
for sub in siteaacess.ru api.siteaacess.ru crawl.siteaacess.ru rag.siteaacess.ru dify.siteaacess.ru grafana.siteaacess.ru; do
    echo "server { listen 80; server_name $sub; return 301 https://\$host\$request_uri; }" >> "$PROJECT_DIR/nginx/conf.d/redirect.conf"
done

docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d nginx certbot 2>/dev/null || \
docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d nginx

echo "SSL configured for $DOMAIN"
