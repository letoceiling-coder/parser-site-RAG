# Parser Site RAG

Автоматический парсинг юридических сайтов РФ и база знаний с AI-агентом.

## Архитектура

```
Сайты (pravo.gov.ru, sudact.ru, ГАС Правосудие...)
    │
    ├── Crawl4AI (JS-сайты, Playwright, stealth, captcha)
    └── Scrapy (статика: КиберЛенинка, pravo.gov.ru)
    │
    ▼
S3 Selectel (сырые данные: HTML, Markdown, JSON)
    │
    ▼
RAGFlow (chunking, embedding, векторный поиск)
    │
    ├── Dify (AI-агент, UI, workflow)
    └── FastAPI Gateway (OpenRouter, REST API)
    │
    ▼
OpenRouter (бесплатные модели с fallback)
```

## Поддомены

| Поддомен | Сервис |
|----------|--------|
| siteaacess.ru | Главная страница |
| api.siteaacess.ru | FastAPI Gateway + Swagger |
| rag.siteaacess.ru | RAGFlow |
| dify.siteaacess.ru | Dify (AI-агент) |
| crawl.siteaacess.ru | Crawl4AI API |
| grafana.siteaacess.ru | Мониторинг |

## Быстрый старт

### 1. DNS-записи (A → 85.117.235.93)

```
siteaacess.ru
api.siteaacess.ru
rag.siteaacess.ru
dify.siteaacess.ru
crawl.siteaacess.ru
grafana.siteaacess.ru
```

### 2. Настройка сервера

```bash
ssh root@85.117.235.93
bash scripts/setup-server.sh
```

### 3. Конфигурация

```bash
cp .env.example .env
# Заполните: OPENROUTER_API_KEY, S3_ACCESS_KEY, S3_SECRET_KEY, пароли
nano .env
```

### 4. Деплой

```bash
bash scripts/deploy.sh
```

### 5. OpenRouter в Dify

```bash
bash scripts/configure-dify-openrouter.sh
```

## OpenRouter — бесплатные модели

Цепочка fallback (configs/openrouter/free_models.yaml):

1. `openrouter/free` — авто-выбор бесплатной модели
2. `qwen/qwen3-coder:free`
3. `meta-llama/llama-3.3-70b-instruct:free`
4. `google/gemma-3-27b-it:free`
5. `deepseek/deepseek-r1:free`

При недоступности модели OpenRouter автоматически переключается на следующую.

## Источники парсинга

Конфигурация: `configs/sources/legal_sites.yaml`

- **Scrapy**: pravo.gov.ru, sudact.ru, cyberleninka.ru, pravo.ru, rg.ru
- **Crawl4AI**: consultant.ru, garant.ru, ГАС Правосудие, kad.arbitr.ru, sudrf.ru

## Обход блокировок и captcha

- Playwright Stealth (скрытие автоматизации)
- Ротация User-Agent
- Прокси (PROXY_ENABLED + PROXY_LIST в .env)
- Retry с exponential backoff
- 2captcha интеграция (CAPTCHA_API_KEY)
- Crawl4AI magic mode + simulate_user

## API

```bash
# Health check
curl https://api.siteaacess.ru/health

# Chat через OpenRouter
curl -X POST https://api.siteaacess.ru/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Что такое исковая давность?"}'

# RAG-запрос
curl -X POST "https://api.siteaacess.ru/api/rag/query?question=Сроки апелляции"

# Запуск парсинга
curl -X POST https://api.siteaacess.ru/api/crawl/start \
  -H "Content-Type: application/json" \
  -d '{"source_id": "pravo_gov"}'
```

## S3 Selectel

```
Endpoint: s3.ru-3.storage.selcloud.ru
Region:   ru-3
Bucket:   knowledge-raw
```

Структура: `raw/{source_id}/{domain}/{date}/{hash}.md`

## Требования к серверу

- CPU: 4+ ядер
- RAM: 16+ GB (RAGFlow + Dify)
- Disk: 50+ GB SSD
- Docker 24+ / Docker Compose 2.26+

## Локальная разработка

```bash
cp .env.example .env
docker compose up -d postgres redis
docker compose up -d api-gateway crawler-crawl4ai
```

## Мониторинг

```bash
docker compose --profile monitoring up -d
# Grafana: https://grafana.siteaacess.ru
```

## Лицензии

- Crawl4AI — Apache 2.0
- Scrapy — BSD
- RAGFlow — Apache 2.0
- Dify — Apache 2.0
