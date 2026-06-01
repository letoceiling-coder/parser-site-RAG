#!/bin/bash
# Настройка host nginx как reverse proxy для Parser Site RAG
# Запуск на сервере: bash scripts/setup-host-nginx.sh

DOMAIN="siteaacess.ru"
CONF="/etc/nginx/sites-available/parser-site-rag"

cat > "$CONF" << 'NGINX'
upstream parser_api {
    server 127.0.0.1:8000;
}
upstream parser_crawl {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name siteaacess.ru www.siteaacess.ru;

    root /opt/parser-site-rag/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://parser_api;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}

server {
    listen 80;
    server_name api.siteaacess.ru;

    location / {
        proxy_pass http://parser_api;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }
}

server {
    listen 80;
    server_name crawl.siteaacess.ru;

    location / {
        proxy_pass http://parser_crawl;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }
}

server {
    listen 80;
    server_name rag.siteaacess.ru;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}

server {
    listen 80;
    server_name dify.siteaacess.ru;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
        proxy_buffering off;
    }
}

server {
    listen 80;
    server_name grafana.siteaacess.ru;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

ln -sf "$CONF" /etc/nginx/sites-enabled/parser-site-rag
nginx -t && systemctl reload nginx
echo "Host nginx configured for $DOMAIN"
