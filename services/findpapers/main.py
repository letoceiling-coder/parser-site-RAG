"""Findpapers service — поиск научных статей для базы знаний."""

from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import datetime, timezone

import boto3
import httpx
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG_PATH = "/app/configs/queries.yaml"


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"queries": [], "sources": {}}


def upload_to_s3(content: str, query: str, source: str) -> str:
    endpoint = os.getenv("S3_ENDPOINT", "")
    if not endpoint or not os.getenv("S3_ACCESS_KEY"):
        return f"local://{query}"

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=os.getenv("S3_REGION", "ru-3"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
    )
    bucket = os.getenv("S3_BUCKET", "knowledge-raw")
    ts = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    key = f"raw/findpapers/{source}/{ts}/{hashlib.md5(query.encode()).hexdigest()}.json"

    s3.put_object(Bucket=bucket, Key=key, Body=content.encode("utf-8"), ContentType="application/json")
    return f"s3://{bucket}/{key}"


async def search_arxiv(query: str, max_results: int = 10) -> list[dict]:
    url = "http://export.arxiv.org/api/query"
    params = {"search_query": f"all:{query}", "max_results": max_results}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return []
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        papers = []
        for entry in root.findall("atom:entry", ns):
            papers.append({
                "title": entry.find("atom:title", ns).text.strip() if entry.find("atom:title", ns) is not None else "",
                "summary": entry.find("atom:summary", ns).text.strip() if entry.find("atom:summary", ns) is not None else "",
                "url": entry.find("atom:id", ns).text if entry.find("atom:id", ns) is not None else "",
            })
        return papers


async def search_semantic_scholar(query: str, max_results: int = 10) -> list[dict]:
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {"query": query, "limit": max_results, "fields": "title,abstract,url,year"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return [
            {"title": p.get("title", ""), "summary": p.get("abstract", ""), "url": p.get("url", ""), "year": p.get("year")}
            for p in data.get("data", [])
        ]


async def run_query(query_config: dict) -> dict:
    query = query_config["query"]
    sources = query_config.get("sources", ["arxiv"])
    results = {}

    for source in sources:
        if source == "arxiv":
            results["arxiv"] = await search_arxiv(query)
        elif source == "semantic_scholar":
            results["semantic_scholar"] = await search_semantic_scholar(query)
        time.sleep(1)

    import json
    content = json.dumps({"query": query, "results": results}, ensure_ascii=False, indent=2)
    path = upload_to_s3(content, query, "combined")
    logger.info("Query '%s' completed, stored at %s", query, path)
    return {"query": query, "storage_path": path, "paper_count": sum(len(v) for v in results.values())}


async def run_all():
    config = load_config()
    for q in config.get("queries", []):
        if q.get("enabled", True):
            await run_query(q)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_all())
