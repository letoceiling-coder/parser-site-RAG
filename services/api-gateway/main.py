"""FastAPI Gateway — единая точка входа для RAG-системы."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from openrouter_client import OpenRouterClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

openrouter = OpenRouterClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API Gateway started")
    yield
    logger.info("API Gateway stopped")


app = FastAPI(
    title="Parser Site RAG API",
    description="API Gateway для парсинга сайтов и базы знаний",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    model: str | None = None
    system_prompt: str | None = "Ты — юридический ассистент. Отвечай на русском языке, опираясь на базу знаний."
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1, le=32000)


class ChatResponse(BaseModel):
    answer: str
    model: str
    usage: dict[str, Any] | None = None


class CrawlRequest(BaseModel):
    source_id: str
    url: str | None = None
    force: bool = False


@app.get("/health")
async def health():
    return {"status": "ok", "service": "api-gateway"}


@app.get("/api/health")
async def api_health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    messages = []
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})
    messages.append({"role": "user", "content": request.message})

    try:
        result = await openrouter.chat(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as e:
        logger.exception("Chat failed")
        raise HTTPException(status_code=502, detail=f"OpenRouter error: {e}")

    choice = result.get("choices", [{}])[0]
    return ChatResponse(
        answer=choice.get("message", {}).get("content", ""),
        model=result.get("model", "unknown"),
        usage=result.get("usage"),
    )


@app.get("/api/models/free")
async def list_free_models():
    try:
        models = await openrouter.list_models()
        return {"models": models, "fallback_chain": openrouter.models}
    except Exception as e:
        return {"models": [], "fallback_chain": openrouter.models, "error": str(e)}


@app.post("/api/crawl/start")
async def start_crawl(request: CrawlRequest):
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "http://crawler-crawl4ai:8001/crawl/start",
                json={"source_id": request.source_id, "url": request.url, "force": request.force},
            )
            return response.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Crawler service unavailable")


@app.get("/api/crawl/status/{task_id}")
async def crawl_status(task_id: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"http://crawler-crawl4ai:8001/crawl/status/{task_id}")
            return response.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Crawler service unavailable")


@app.get("/api/sources")
async def list_sources():
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get("http://crawler-crawl4ai:8001/sources")
            return response.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Crawler service unavailable")


@app.get("/api/ragflow/knowledge-bases")
async def ragflow_knowledge_bases():
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(f"{settings.ragflow_url}/api/v1/datasets")
            if response.status_code == 200:
                return response.json()
            return {"status": "ragflow_unavailable", "detail": response.text[:200]}
        except httpx.ConnectError:
            return {"status": "ragflow_unavailable", "detail": "RAGFlow not running"}


@app.post("/api/rag/query")
async def rag_query(question: str, knowledge_base_id: str | None = None):
    """RAG-запрос: поиск в базе знаний + генерация ответа через OpenRouter."""
    context = ""
    if knowledge_base_id:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                search_resp = await client.post(
                    f"{settings.ragflow_url}/api/v1/retrieval",
                    json={"question": question, "dataset_id": knowledge_base_id},
                )
                if search_resp.status_code == 200:
                    chunks = search_resp.json().get("data", {}).get("chunks", [])
                    context = "\n\n".join(c.get("content", "") for c in chunks[:5])
            except httpx.ConnectError:
                pass

    system = "Ты — юридический ассистент. Отвечай на русском, опираясь на предоставленный контекст."
    if context:
        system += f"\n\nКонтекст из базы знаний:\n{context}"

    result = await openrouter.chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]
    )
    choice = result.get("choices", [{}])[0]
    return {
        "answer": choice.get("message", {}).get("content", ""),
        "model": result.get("model"),
        "context_used": bool(context),
    }
