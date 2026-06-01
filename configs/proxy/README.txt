Прокси для парсинга судебных баз (kad.arbitr.ru, sudrf.ru, ГАС Правосудие)

Зачем нужны:
- Сайты блокируют IP при частых запросах
- Residential/мобильные прокси РФ выглядят как обычные пользователи
- Ротация IP снижает риск captcha и 403

Формат PROXY_LIST:
  http://login:password@host:port,http://login2:password2@host2:port

Рекомендуемые провайдеры для РФ (платные, для продакшена):
  - mobileproxy.space (мобильные РФ)
  - proxy6.net (IPv4 РФ)
  - brightdata.com (residential)

Тестовый режим:
  Сервис proxy-rotator автоматически подбирает бесплатные прокси.
  Для судебных баз лучше купить 2-3 мобильных прокси РФ и добавить в .env
