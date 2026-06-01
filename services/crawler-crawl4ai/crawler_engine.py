"""Crawl4AI crawler engine with stealth, proxy rotation, and captcha bypass."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import random
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import boto3
import httpx
import yaml
from fake_useragent import UserAgent
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class CrawlerSettings(BaseSettings):
    s3_endpoint: str = ""
    s3_region: str = "ru-3"
    s3_bucket: str = "knowledge-raw"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    captcha_service: str = ""
    captcha_api_key: str = ""
    proxy_enabled: bool = False
    proxy_list: str = ""
    ragflow_url: str = "http://localhost:9380"

    class Config:
        env_file = ".env"


settings = CrawlerSettings()
ua = UserAgent()


def load_sources() -> list[dict]:
    config_path = "/app/configs/sources/legal_sites.yaml"
    if os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return [s for s in data.get("sources", []) if s.get("type") == "crawl4ai" and s.get("enabled", True)]
    return []


def get_proxies() -> list[str]:
    if not settings.proxy_enabled or not settings.proxy_list:
        return []
    return [p.strip() for p in settings.proxy_list.split(",") if p.strip()]


async def solve_captcha_2captcha(site_key: str, page_url: str, captcha_type: str = "recaptcha") -> str | None:
    if not settings.captcha_api_key:
        logger.warning("Captcha detected but no API key configured")
        return None

    api_url = "https://2captcha.com"
    async with httpx.AsyncClient(timeout=180.0) as client:
        submit_data = {
            "key": settings.captcha_api_key,
            "method": "userrecaptcha" if captcha_type == "recaptcha" else "hcaptcha",
            "googlekey": site_key,
            "pageurl": page_url,
            "json": 1,
        }
        resp = await client.post(f"{api_url}/in.php", data=submit_data)
        result = resp.json()
        if result.get("status") != 1:
            logger.error("2captcha submit failed: %s", result)
            return None

        task_id = result["request"]
        for _ in range(60):
            await asyncio.sleep(5)
            check = await client.get(
                f"{api_url}/res.php",
                params={"key": settings.captcha_api_key, "action": "get", "id": task_id, "json": 1},
            )
            check_result = check.json()
            if check_result.get("status") == 1:
                return check_result["request"]
            if check_result.get("request") != "CAPCHA_NOT_READY":
                logger.error("2captcha solve failed: %s", check_result)
                return None
    return None


def upload_to_s3(content: str, url: str, source_id: str, fmt: str = "md") -> str:
    if not settings.s3_access_key:
        local_path = f"/app/data/{source_id}/{hashlib.md5(url.encode()).hexdigest()}.{fmt}"
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(content)
        return local_path

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )
    domain = urlparse(url).netloc
    timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    key = f"raw/{source_id}/{domain}/{timestamp}/{hashlib.md5(url.encode()).hexdigest()}.{fmt}"

    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=content.encode("utf-8"),
        ContentType="text/markdown" if fmt == "md" else "text/html",
        Metadata={"source_url": url, "source_id": source_id},
    )
    return f"s3://{settings.s3_bucket}/{key}"


async def crawl_url(
    url: str,
    source_id: str,
    stealth: bool = True,
    captcha_enabled: bool = False,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Crawl a single URL with Crawl4AI, stealth mode, and retry logic."""
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

    proxies = get_proxies()
    proxy = random.choice(proxies) if proxies else None
    user_agent = ua.random

    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        proxy=proxy,
        user_agent=user_agent,
        extra_args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
        ],
    )

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=10,
        remove_overlay_elements=True,
        magic=True,
        simulate_user=True,
        override_navigator=True,
        wait_until="networkidle",
        page_timeout=60000,
        delay_before_return_html=2.0,
    )

    last_error = None
    for attempt in range(max_retries):
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                if stealth:
                    try:
                        from playwright_stealth import stealth_async
                        await stealth_async(crawler.crawler_strategy.browser_manager.default_context)
                    except Exception:
                        pass

                result = await crawler.arun(url=url, config=run_config)

                if not result.success:
                    last_error = result.error_message
                    wait = (2 ** attempt) + random.uniform(1, 3)
                    logger.warning("Attempt %d failed for %s: %s. Retry in %.1fs", attempt + 1, url, last_error, wait)
                    await asyncio.sleep(wait)
                    continue

                markdown = result.markdown or ""
                html = result.html or ""

                if captcha_enabled and ("captcha" in html.lower() or "recaptcha" in html.lower()):
                    logger.info("Captcha detected on %s, attempting solve...", url)
                    token = await solve_captcha_2captcha("", url)
                    if token:
                        result = await crawler.arun(url=url, config=run_config)
                        markdown = result.markdown or markdown

                storage_path = upload_to_s3(markdown, url, source_id, "md")
                if html:
                    upload_to_s3(html, url, source_id, "html")

                return {
                    "success": True,
                    "url": url,
                    "source_id": source_id,
                    "markdown_length": len(markdown),
                    "storage_path": storage_path,
                    "title": result.metadata.get("title", "") if result.metadata else "",
                }

        except Exception as e:
            last_error = str(e)
            wait = (2 ** attempt) + random.uniform(2, 5)
            logger.warning("Exception on attempt %d for %s: %s. Retry in %.1fs", attempt + 1, url, e, wait)
            await asyncio.sleep(wait)

        if attempt < max_retries - 1:
            browser_config.user_agent = ua.random
            if proxies:
                browser_config.proxy = random.choice(proxies)

    return {"success": False, "url": url, "source_id": source_id, "error": last_error}


async def crawl_source(source: dict) -> dict[str, Any]:
    """Crawl all pages for a configured source."""
    source_id = source["id"]
    base_url = source["url"]
    stealth = source.get("stealth", True)
    captcha = source.get("captcha", False)

    logger.info("Starting crawl for source: %s (%s)", source_id, base_url)
    result = await crawl_url(base_url, source_id, stealth=stealth, captcha_enabled=captcha)

    if result["success"] and settings.ragflow_url:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    f"{settings.ragflow_url}/api/v1/document/upload",
                    json={"source_id": source_id, "storage_path": result["storage_path"]},
                )
        except Exception as e:
            logger.warning("RAGFlow upload notification failed: %s", e)

    return result
