#!/bin/bash
set -euo pipefail
# ФИНАЛЬНЫЙ ФИКС Dify: только бесплатные модели OpenRouter

cd /opt/parser-site-rag
TENANT_ID="a528d4cf-523b-4c2c-809a-2f10bcbbb529"
PROVIDER="langgenius/openrouter/openrouter"
PRIMARY="meta-llama/llama-3.3-70b-instruct:free"

PLUGIN_DIR=$(docker exec dify-plugin_daemon-1 find /app/storage/cwd/langgenius -maxdepth 1 -name 'openrouter-*' -type d | head -1)
LLM_DIR="${PLUGIN_DIR}/models/llm"
EMBED_DIR="${PLUGIN_DIR}/models/text_embedding"
BACKUP="${PLUGIN_DIR}/models/llm_paid_backup"

echo "=== FINAL Dify free-only fix ==="

# FREE yaml + _position.yaml (критично!)
for f in configs/dify/models/free-*.yaml configs/dify/models/_position.yaml; do
  docker cp "$f" "dify-plugin_daemon-1:${LLM_DIR}/$(basename $f)"
done

# Убрать платные LLM (если вернулись)
docker exec dify-plugin_daemon-1 sh -c "
  mkdir -p ${BACKUP}
  cd ${LLM_DIR}
  for f in *.yaml; do
    case \"\$f\" in
      free-*|_position.yaml) ;;
      *) mv \"\$f\" ${BACKUP}/ 2>/dev/null || true ;;
    esac
  done
  ls -1 *.yaml
"

# Убрать платные embedding
docker exec dify-plugin_daemon-1 sh -c "
  mkdir -p ${PLUGIN_DIR}/models/embed_paid_backup
  cd ${EMBED_DIR}
  for f in *.yaml; do mv \"\$f\" ${PLUGIN_DIR}/models/embed_paid_backup/ 2>/dev/null || true; done
  ls -1 2>/dev/null || echo 'no embeddings'
"

# Очистить ВСЕ кеши plugin в Redis
docker exec dify-redis-1 redis-cli KEYS 'plugin*' | while read -r k; do
  [ -n "$k" ] && docker exec dify-redis-1 redis-cli DEL "$k"
done

docker exec dify-db_postgres-1 psql -U postgres -d dify -c \
  "DELETE FROM provider_model_settings WHERE tenant_id='${TENANT_ID}';"

docker exec dify-db_postgres-1 psql -U postgres -d dify -c \
  "UPDATE tenant_default_models SET provider_name='${PROVIDER}', model_name='${PRIMARY}', updated_at=NOW() WHERE tenant_id='${TENANT_ID}' AND model_type='llm';"

docker exec dify-db_postgres-1 psql -U postgres -d dify -c \
  "DELETE FROM tenant_default_models WHERE tenant_id='${TENANT_ID}' AND model_type IN ('text-embedding','rerank','speech2text','tts');"

docker exec dify-db_postgres-1 psql -U postgres -d dify -c \
  "UPDATE providers SET is_valid=true WHERE provider_name='${PROVIDER}';"

docker restart dify-plugin_daemon-1 dify-api-1 dify-worker-1 dify-web-1 dify-redis-1
sleep 12

echo "Models in plugin:"
docker exec dify-plugin_daemon-1 ls "${LLM_DIR}/"

echo ""
echo "DONE. Refresh dify.siteaacess.ru (Ctrl+Shift+R)"
echo "OpenRouter -> 6 models with FREE in name"
echo "System model -> FREE Llama 3.3 70B"
