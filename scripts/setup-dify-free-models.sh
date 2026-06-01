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

# Отключить ВСЕ predefined модели плагина
echo "Disabling paid models..."
docker exec dify-plugin_daemon-1 sh -c "ls ${LLM_DIR}/*.yaml" | while read -r ypath; do
  model=$(docker exec dify-plugin_daemon-1 grep '^model:' "$ypath" | head -1 | sed 's/model: //' | tr -d '"' | tr -d "'")
  fname=$(basename "$ypath")
  if [[ "$fname" == free-* ]]; then
    enabled="true"
  else
    enabled="false"
  fi
  docker exec dify-db_postgres-1 psql -U postgres -d dify -q -c \
    "DELETE FROM provider_model_settings WHERE tenant_id='${TENANT_ID}' AND provider_name='${PROVIDER}' AND model_name='${model}';"
  docker exec dify-db_postgres-1 psql -U postgres -d dify -q -c \
    "INSERT INTO provider_model_settings (tenant_id, provider_name, model_name, model_type, enabled, load_balancing_enabled) VALUES ('${TENANT_ID}', '${PROVIDER}', '${model}', 'llm', ${enabled}, false);"
done

# Системная модель по умолчанию
docker exec dify-db_postgres-1 psql -U postgres -d dify -c \
  "UPDATE tenant_default_models SET provider_name='${PROVIDER}', model_name='${PRIMARY}', updated_at=NOW() WHERE tenant_id='${TENANT_ID}' AND model_type='llm';"

docker exec dify-db_postgres-1 psql -U postgres -d dify -c \
  "DELETE FROM tenant_default_models WHERE tenant_id='${TENANT_ID}' AND model_type='text-embedding';"

# Перезапуск
docker restart dify-plugin_daemon-1 dify-api-1 dify-worker-1 dify-web-1
sleep 8

echo ""
echo "=== Done ==="
echo "Default LLM: ${PRIMARY}"
echo "In Dify UI search: FREE"
echo "Available: FREE Llama 3.3 70B, FREE Qwen3 Coder, FREE Gemma 4 31B, ..."
