#!/bin/bash
set -euo pipefail

# Полный деплой Parser Site RAG
# Запуск на сервере: bash scripts/deploy.sh

DOMAIN="${DOMAIN:-siteaacess.ru}"
PROJECT_DIR="${PROJECT_DIR:-/opt/parser-site-rag}"
cd "$PROJECT_DIR"

echo "=== Deploy Parser Site RAG ==="

# Pull latest
git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || true

# ─── RAGFlow ─────────────────────────────────────────────────
RAGFLOW_DIR="$PROJECT_DIR/vendor/ragflow"
if [ ! -d "$RAGFLOW_DIR" ]; then
    echo "Cloning RAGFlow..."
    git clone --depth 1 --branch v0.24.0 https://github.com/infiniflow/ragflow.git "$RAGFLOW_DIR"
fi

if [ -d "$RAGFLOW_DIR/docker" ]; then
    cd "$RAGFLOW_DIR/docker"
    if [ ! -f .env ]; then
        cp .env.example .env 2>/dev/null || cp .env .env.bak 2>/dev/null || true
        sed -i "s/SVR_HTTP_PORT=9380/SVR_HTTP_PORT=9380/" .env 2>/dev/null || true
        sed -i "s/SVR_WEB_HTTP_PORT=80/SVR_WEB_HTTP_PORT=8080/" .env 2>/dev/null || true
    fi
    docker compose -f docker-compose.yml --profile cpu up -d 2>/dev/null || \
    docker compose -f docker-compose.yml up -d 2>/dev/null || true
    cd "$PROJECT_DIR"
    echo "RAGFlow started on port 8080"
fi

# ─── Dify ────────────────────────────────────────────────────
DIFY_DIR="$PROJECT_DIR/vendor/dify"
if [ ! -d "$DIFY_DIR" ]; then
    echo "Cloning Dify..."
    git clone --depth 1 https://github.com/langgenius/dify.git "$DIFY_DIR"
fi

if [ -d "$DIFY_DIR/docker" ]; then
    cd "$DIFY_DIR/docker"
    if [ ! -f .env ]; then
        cp .env.example .env
    fi
    # Настройка портов и домена
    sed -i "s/EXPOSE_NGINX_PORT=80/EXPOSE_NGINX_PORT=8081/" .env 2>/dev/null || true
    sed -i "s|CONSOLE_API_URL=.*|CONSOLE_API_URL=https://dify.$DOMAIN|" .env 2>/dev/null || true
    sed -i "s|CONSOLE_WEB_URL=.*|CONSOLE_WEB_URL=https://dify.$DOMAIN|" .env 2>/dev/null || true
    sed -i "s|APP_API_URL=.*|APP_API_URL=https://dify.$DOMAIN|" .env 2>/dev/null || true
    sed -i "s|APP_WEB_URL=.*|APP_WEB_URL=https://dify.$DOMAIN|" .env 2>/dev/null || true

    docker compose up -d
    cd "$PROJECT_DIR"
    echo "Dify started on port 8081"
fi

# ─── Основной стек ───────────────────────────────────────────
cd "$PROJECT_DIR"
docker compose build
docker compose up -d
docker compose --profile monitoring up -d 2>/dev/null || true

# ─── SSL (Let's Encrypt) ─────────────────────────────────────
if [ "${SETUP_SSL:-true}" = "true" ]; then
    bash scripts/init-ssl.sh || echo "SSL setup skipped or failed — configure manually"
fi

echo ""
echo "=== Deploy complete ==="
echo "  Main:    http://$DOMAIN"
echo "  API:     http://api.$DOMAIN/docs"
echo "  RAG:     http://rag.$DOMAIN"
echo "  Dify:    http://dify.$DOMAIN"
echo "  Crawler: http://crawl.$DOMAIN/docs"
echo "  Grafana: http://grafana.$DOMAIN"
echo ""
echo "Проверка: curl http://api.$DOMAIN/health"
