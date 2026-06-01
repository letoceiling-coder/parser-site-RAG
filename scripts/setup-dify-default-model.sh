#!/bin/bash
# Установка openrouter/free как системной модели Dify через Console API
set -euo pipefail

DIFY_URL="${DIFY_URL:-http://127.0.0.1:8081}"
EMAIL="${DIFY_ADMIN_EMAIL:-letoceiling@gmail.com}"
PASSWORD="${DIFY_ADMIN_PASSWORD:-}"

if [ -z "$PASSWORD" ]; then
    echo "DIFY_ADMIN_PASSWORD не задан — настройка через UI:"
    echo "  1. dify.siteaacess.ru → Настройки → Поставщик модели"
    echo "  2. OpenRouter → Добавить модель → openrouter/free"
    echo "  3. Нажать синюю кнопку «Настройки системной модели»"
    echo "  4. LLM → openrouter/free → Сохранить"
    exit 0
fi

TOKEN=$(curl -s -X POST "${DIFY_URL}/console/api/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"remember_me\":true}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('access_token',''))" 2>/dev/null || true)

if [ -z "$TOKEN" ]; then
    echo "Не удалось войти в Dify. Настройте модель вручную (см. инструкцию выше)."
    exit 0
fi

curl -s -X POST "${DIFY_URL}/console/api/workspaces/current/default-model" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "model_settings": [
            {"model_type": "llm", "provider": "openrouter", "model": "openrouter/free"},
            {"model_type": "text-embedding", "provider": "openrouter", "model": "openai/text-embedding-3-small"},
            {"model_type": "rerank", "provider": "openrouter", "model": "openrouter/free"}
        ]
    }' && echo "Default model set to openrouter/free"
