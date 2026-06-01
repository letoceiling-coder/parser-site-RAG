import random
import os
from scrapy import signals
from fake_useragent import UserAgent

ua = UserAgent()


class RotateUserAgentMiddleware:
    def process_request(self, request, spider):
        request.headers["User-Agent"] = ua.random


class ProxyMiddleware:
    def __init__(self):
        proxy_list = os.getenv("PROXY_LIST", "")
        self.proxies = [p.strip() for p in proxy_list.split(",") if p.strip()] if os.getenv("PROXY_ENABLED") == "true" else []

    def process_request(self, request, spider):
        if self.proxies:
            request.meta["proxy"] = random.choice(self.proxies)
