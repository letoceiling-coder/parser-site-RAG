#!/bin/bash
set -euo pipefail

DOMAIN="${DOMAIN:-siteaacess.ru}"
PROJECT_DIR="${PROJECT_DIR:-/opt/parser-site-rag}"
cd "$PROJECT_DIR"

echo "=== Deploy Parser Site RAG ==="

git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || true

# ─── RAGFlow ─────────────────────────────────────────────────
RAGFLOW_DIR="$PROJECT_DIR/vendor/ragflow"
if [ ! -d "$RAGFLOW_DIR" ]; then
    echo "Cloning RAGFlow..."
    git clone --depth 1 --branch v0.24.0 https://github.com/infiniflow/ragflow.git "$RAGFLOW_DIR"
fi

cd "$RAGFLOW_DIR/docker"
if [ ! -f .env ]; then
    cp .env .env.bak 2>/dev/null || true
fi
# Порты: web=8080, api=9380
grep -q 'SVR_WEB_HTTP_PORT=8080' .env || sed -i 's/SVR_WEB_HTTP_PORT=.*/SVR_WEB_HTTP_PORT=8080/' .env
grep -q 'SVR_HTTP_PORT=9380' .env || sed -i 's/SVR_HTTP_PORT=.*/SVR_HTTP_PORT=9380/' .env

docker compose -p ragflow --profile cpu up -d 2>/dev/null || \
docker compose -p ragflow up -d ragflow-cpu 2>/dev/null || \
docker compose -p ragflow up -d
echo "RAGFlow started (ports 8080/9380)"
cd "$PROJECT_DIR"

# ─── Dify ────────────────────────────────────────────────────
DIFY_DIR="$PROJECT_DIR/vendor/dify"
if [ ! -d "$DIFY_DIR" ]; then
    echo "Cloning Dify..."
    git clone --depth 1 https://github.com/langgenius/dify.git "$DIFY_DIR"
fi

cd "$DIFY_DIR/docker"
if [ ! -f .env ]; then
    cp .env.example .env
fi

# Порт 8081, без SSL (SSL через host nginx)
sed -i 's/EXPOSE_NGINX_PORT=.*/EXPOSE_NGINX_PORT=8081/' .env
sed -i 's/EXPOSE_NGINX_SSL_PORT=.*/EXPOSE_NGINX_SSL_PORT=8443/' .env
sed -i "s|CONSOLE_API_URL=.*|CONSOLE_API_URL=http://dify.$DOMAIN|" .env 2>/dev/null || true
sed -i "s|CONSOLE_WEB_URL=.*|CONSOLE_WEB_URL=http://dify.$DOMAIN|" .env 2>/dev/null || true
sed -i "s|APP_API_URL=.*|APP_API_URL=http://dify.$DOMAIN|" .env 2>/dev/null || true
sed -i "s|APP_WEB_URL=.*|APP_WEB_URL=http://dify.$DOMAIN|" .env 2>/dev/null || true
sed -i 's/NGINX_HTTPS_ENABLED=true/NGINX_HTTPS_ENABLED=false/' .env 2>/dev/null || true

docker compose -p dify up -d
echo "Dify started on port 8081"
cd "$PROJECT_DIR"

# ─── Основной стек ───────────────────────────────────────────
docker compose build
docker compose up -d
docker compose --profile monitoring up -d 2>/dev/null || true

# ─── Host nginx ──────────────────────────────────────────────
bash scripts/setup-host-nginx.sh

# ─── SSL ─────────────────────────────────────────────────────
if [ "${SETUP_SSL:-false}" = "true" ]; then
    bash scripts/init-ssl.sh || echo "SSL setup skipped"
fi

echo ""
echo "=== Deploy complete ==="
echo "  Main:    http://$DOMAIN"
echo "  API:     http://api.$DOMAIN/docs"
echo "  RAG:     http://rag.$DOMAIN"
echo "  Dify:    http://dify.$DOMAIN"
echo "  Crawler: http://crawl.$DOMAIN/docs"
