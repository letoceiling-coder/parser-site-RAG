# Scrapy settings
BOT_NAME = 'legal_crawler'

SPIDER_MODULES = ['spiders']
NEWSPIDER_MODULE = 'spiders'

ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
    'middlewares.RotateUserAgentMiddleware': 400,
    'middlewares.ProxyMiddleware': 410,
}

RETRY_ENABLED = True
RETRY_TIMES = 5
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 30

ITEM_PIPELINES = {
    'pipelines.S3Pipeline': 300,
}

LOG_LEVEL = 'INFO'

import os
S3_ENDPOINT = os.getenv('S3_ENDPOINT', '')
S3_REGION = os.getenv('S3_REGION', 'ru-3')
S3_BUCKET = os.getenv('S3_BUCKET', 'knowledge-raw')
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY', '')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY', '')
