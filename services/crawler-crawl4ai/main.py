"""Crawl4AI FastAPI service."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from crawler_engine import crawl_source, load_sources

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Crawl4AI Service", version="1.0.0")

tasks_store: dict[str, dict[str, Any]] = {}


class CrawlStartRequest(BaseModel):
    source_id: str
    url: str | None = None
    force: bool = False


@app.get("/health")
async def health():
    return {"status": "ok", "service": "crawl4ai"}


@app.get("/sources")
async def list_sources():
    sources = load_sources()
    return {"sources": sources, "total": len(sources)}


@app.post("/crawl/start")
async def start_crawl(request: CrawlStartRequest, background_tasks: BackgroundTasks):
    sources = load_sources()
    source = next((s for s in sources if s["id"] == request.source_id), None)

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{request.source_id}' not found")

    if request.url:
        source = {**source, "url": request.url}

    task_id = str(uuid.uuid4())
    tasks_store[task_id] = {"status": "pending", "source_id": request.source_id}

    async def run_crawl():
        tasks_store[task_id]["status"] = "running"
        try:
            result = await crawl_source(source)
            tasks_store[task_id] = {"status": "completed", **result}
        except Exception as e:
            tasks_store[task_id] = {"status": "failed", "error": str(e)}

    background_tasks.add_task(run_crawl)
    return {"task_id": task_id, "status": "pending", "source_id": request.source_id}


@app.get("/crawl/status/{task_id}")
async def crawl_status(task_id: str):
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_store[task_id]


@app.post("/crawl/all")
async def crawl_all(background_tasks: BackgroundTasks):
    sources = load_sources()
    task_ids = []

    for source in sources:
        task_id = str(uuid.uuid4())
        tasks_store[task_id] = {"status": "pending", "source_id": source["id"]}
        task_ids.append(task_id)

        async def run(source=source, tid=task_id):
            tasks_store[tid]["status"] = "running"
            try:
                result = await crawl_source(source)
                tasks_store[tid] = {"status": "completed", **result}
            except Exception as e:
                tasks_store[tid] = {"status": "failed", "error": str(e)}

        background_tasks.add_task(run)

    return {"task_ids": task_ids, "total": len(sources)}
