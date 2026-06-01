#!/bin/bash
set -euo pipefail
# Install free OpenRouter models into Dify plugin and set defaults

cd /opt/parser-site-rag
TENANT_ID="a528d4cf-523b-4c2c-809a-2f10bcbbb529"
PROVIDER="langgenius/openrouter/openrouter"
PRIMARY="meta-llama/llama-3.3-70b-instruct:free"

PLUGIN_DIR=$(docker exec dify-plugin_daemon-1 find /app/storage/cwd -maxdepth 1 -name 'openrouter-*' -type d | head -1)
LLM_DIR="${PLUGIN_DIR}/models/llm"

echo "Plugin: $PLUGIN_DIR"

for f in configs/dify/models/*.yaml; do
    fname=$(basename "$f")
    docker cp "$f" "dify-plugin_daemon-1:${LLM_DIR}/${fname}"
    echo "Installed $fname"
done

docker exec dify-db_postgres-1 psql -U postgres -d dify -c \
  "UPDATE tenant_default_models SET provider_name='${PROVIDER}', model_name='${PRIMARY}', updated_at=NOW() WHERE tenant_id='${TENANT_ID}' AND model_type='llm';"

docker exec dify-db_postgres-1 psql -U postgres -d dify -c \
  "DELETE FROM tenant_default_models WHERE tenant_id='${TENANT_ID}' AND model_type='text-embedding';"

# Disable Auto Router and paid models
for model in openrouter/auto gpt-4o gpt-4o-mini gpt-4 gpt-3.5-turbo gpt-5 gpt-5.1 o3-mini openai/text-embedding-3-large openai/text-embedding-3-small; do
    docker exec dify-db_postgres-1 psql -U postgres -d dify -c \
      "INSERT INTO provider_model_settings (tenant_id, provider_name, model_name, model_type, enabled, load_balancing_enabled) VALUES ('${TENANT_ID}', '${PROVIDER}', '${model}', 'llm', false, false) ON CONFLICT DO NOTHING;" 2>/dev/null || true
done

docker restart dify-plugin_daemon-1 dify-api-1 dify-worker-1 dify-web-1
echo "Done. Primary LLM: ${PRIMARY}"
