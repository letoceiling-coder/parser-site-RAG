#!/bin/bash
set -euo pipefail

# Настройка сервера Ubuntu/Debian для Parser Site RAG
# Запуск: bash scripts/setup-server.sh

DOMAIN="${DOMAIN:-siteaacess.ru}"
PROJECT_DIR="/opt/parser-site-rag"

echo "=== Настройка сервера для $DOMAIN ==="

# Обновление системы
apt-get update && apt-get upgrade -y

# Docker
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# Docker Compose plugin
apt-get install -y docker-compose-plugin git curl wget certbot

# Firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Swap (минимум 8GB для RAGFlow + Dify)
if [ ! -f /swapfile ]; then
    fallocate -l 8G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# Клонирование репозитория
if [ ! -d "$PROJECT_DIR" ]; then
    git clone git@github.com:letoceiling-coder/parser-site-RAG.git "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Отредактируйте $PROJECT_DIR/.env перед запуском!"
fi

# DNS subdomains reminder
echo ""
echo "=== Необходимые DNS A-записи для $DOMAIN ==="
echo "  $DOMAIN              -> $(curl -s ifconfig.me 2>/dev/null || echo 'SERVER_IP')"
echo "  api.$DOMAIN          -> SERVER_IP"
echo "  rag.$DOMAIN          -> SERVER_IP"
echo "  dify.$DOMAIN         -> SERVER_IP"
echo "  crawl.$DOMAIN        -> SERVER_IP"
echo "  grafana.$DOMAIN      -> SERVER_IP"
echo ""

echo "=== Сервер готов. Следующий шаг: bash scripts/deploy.sh ==="
