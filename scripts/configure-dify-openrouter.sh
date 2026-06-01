#!/bin/bash
# Настройка Dify для работы с OpenRouter (бесплатные модели)
# Запуск после первого входа в Dify: bash scripts/configure-dify-openrouter.sh

DOMAIN="${DOMAIN:-siteaacess.ru}"
OPENROUTER_KEY="${OPENROUTER_API_KEY:-}"

if [ -z "$OPENROUTER_KEY" ]; then
    echo "Установите OPENROUTER_API_KEY в .env"
    exit 1
fi

echo "=== Настройка OpenRouter в Dify ==="
echo ""
echo "Выполните вручную в Dify (https://dify.$DOMAIN):"
echo ""
echo "1. Settings → Model Provider → OpenRouter"
echo "   API Key: $OPENROUTER_KEY"
echo ""
echo "2. Добавьте модели (только бесплатные):"
echo "   - openrouter/free"
echo "   - qwen/qwen3-coder:free"
echo "   - meta-llama/llama-3.3-70b-instruct:free"
echo "   - google/gemma-3-27b-it:free"
echo "   - deepseek/deepseek-r1:free"
echo ""
echo "3. Создайте Knowledge Base → подключите RAGFlow dataset"
echo "4. Создайте Agent/Chatbot → выберите openrouter/free как основную модель"
echo "5. В System Prompt укажите: 'Ты юридический ассистент. Отвечай на русском.'"
echo ""
echo "Fallback настроен автоматически через OpenRouter API (models array)"
