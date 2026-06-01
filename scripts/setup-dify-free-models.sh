#!/bin/bash
set -euo pipefail
# Dify: только бесплатные OpenRouter модели (префикс FREE в списке)

cd /opt/parser-site-rag
TENANT_ID="a528d4cf-523b-4c2c-809a-2f10bcbbb529"
PROVIDER="langgenius/openrouter/openrouter"
PRIMARY="meta-llama/llama-3.3-70b-instruct:free"

PLUGIN_DIR=$(docker exec dify-plugin_daemon-1 find /app/storage/cwd/langgenius -maxdepth 1 -name 'openrouter-*' -type d | head -1)
LLM_DIR="${PLUGIN_DIR}/models/llm"

echo "=== Dify FREE models setup ==="
echo "Plugin: $PLUGIN_DIR"

# Удалить сломанные YAML (без кавычек вокруг :free)
docker exec dify-plugin_daemon-1 rm -f \
  "${LLM_DIR}/meta-llama-llama-3.3-70b-instruct-free.yaml" \
  "${LLM_DIR}/qwen-qwen3-coder-free.yaml" \
  "${LLM_DIR}/google-gemma-4-31b-it-free.yaml" 2>/dev/null || true

# Установить FREE-модели (model ID в кавычках!)
for f in configs/dify/models/free-*.yaml; do
  fname=$(basename "$f")
  docker cp "$f" "dify-plugin_daemon-1:${LLM_DIR}/${fname}"
  echo "  + $fname"
done

# Перезапуск
docker restart dify-plugin_daemon-1 dify-api-1 dify-worker-1 dify-web-1
sleep 5
python3 scripts/disable-dify-paid-models.py
