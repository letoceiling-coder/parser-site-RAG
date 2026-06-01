import json
import random
import os
from fake_useragent import UserAgent

ua = UserAgent()


def _load_proxies() -> list[str]:
    if os.getenv("PROXY_ENABLED") != "true":
        return []
    proxy_list = os.getenv("PROXY_LIST", "")
    if proxy_list.strip():
        return [p.strip() for p in proxy_list.split(",") if p.strip()]
    for path in ("/app/data/proxies.json", "/app/data/crawl4ai/proxies.json"):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f).get("proxies", [])
    return []


class RotateUserAgentMiddleware:
    def process_request(self, request, spider):
        request.headers["User-Agent"] = ua.random


class ProxyMiddleware:
    def __init__(self):
        self.proxies = _load_proxies()

    def process_request(self, request, spider):
        if self.proxies:
            request.meta["proxy"] = random.choice(self.proxies)
