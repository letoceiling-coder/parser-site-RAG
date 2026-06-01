#!/bin/bash
set -euo pipefail
# Оставить в Dify ТОЛЬКО бесплатные модели OpenRouter

cd /opt/parser-site-rag
TENANT_ID="a528d4cf-523b-4c2c-809a-2f10bcbbb529"
PROVIDER="langgenius/openrouter/openrouter"
PRIMARY="meta-llama/llama-3.3-70b-instruct:free"

PLUGIN_DIR=$(docker exec dify-plugin_daemon-1 find /app/storage/cwd/langgenius -maxdepth 1 -name 'openrouter-*' -type d | head -1)
LLM_DIR="${PLUGIN_DIR}/models/llm"
BACKUP_DIR="${PLUGIN_DIR}/models/llm_paid_backup"

echo "=== Dify: only FREE models ==="

# Установить FREE yaml
for f in configs/dify/models/free-*.yaml; do
  docker cp "$f" "dify-plugin_daemon-1:${LLM_DIR}/$(basename $f)"
done

# Перенести все платные модели в backup (оставить только free-*.yaml)
docker exec dify-plugin_daemon-1 mkdir -p "$BACKUP_DIR"
docker exec dify-plugin_daemon-1 sh -c "
  cd ${LLM_DIR}
  for f in *.yaml; do
    case \"\$f\" in
      free-*) ;;
      *) mv \"\$f\" ${BACKUP_DIR}/ 2>/dev/null || true ;;
    esac
  done
  echo \"Active models:\"
  ls -1 *.yaml 2>/dev/null || echo none
"

# Очистить settings — Dify покажет только оставшиеся модели
docker exec dify-db_postgres-1 psql -U postgres -d dify -c \
  "DELETE FROM provider_model_settings WHERE tenant_id='${TENANT_ID}' AND provider_name='${PROVIDER}';"

docker exec dify-db_postgres-1 psql -U postgres -d dify -c \
  "UPDATE tenant_default_models SET provider_name='${PROVIDER}', model_name='${PRIMARY}', updated_at=NOW() WHERE tenant_id='${TENANT_ID}' AND model_type='llm';"

docker exec dify-db_postgres-1 psql -U postgres -d dify -c \
  "DELETE FROM tenant_default_models WHERE tenant_id='${TENANT_ID}' AND model_type='text-embedding';"

# Убедиться что провайдер valid
docker exec dify-db_postgres-1 psql -U postgres -d dify -c \
  "UPDATE providers SET is_valid=true WHERE provider_name='${PROVIDER}';"

docker restart dify-plugin_daemon-1 dify-api-1 dify-worker-1 dify-web-1
sleep 10

echo "Done. OpenRouter restored with 6 FREE models only."
echo "Refresh dify.siteaacess.ru -> Settings -> Model Provider"
