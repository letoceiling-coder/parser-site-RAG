"""OpenRouter client with free model fallback chain."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx
import yaml

from config import settings

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("/app/configs/openrouter/free_models.yaml")


def load_free_models() -> list[str]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("models", [])
    return [
        "openrouter/free",
        "qwen/qwen3-coder:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-3-27b-it:free",
        "deepseek/deepseek-r1:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
    ]


class OpenRouterClient:
    def __init__(self) -> None:
        self.base_url = settings.openrouter_base_url
        self.api_key = settings.openrouter_api_key
        self.models = load_free_models()

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> dict[str, Any]:
        primary = model or self.models[0]
        fallback_models = [primary] + [m for m in self.models if m != primary]

        payload = {
            "model": primary,
            "models": fallback_models,
            "route": "fallback",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": f"https://{settings.domain}",
            "X-Title": "Parser Site RAG",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )

            if response.status_code != 200:
                logger.error("OpenRouter error %s: %s", response.status_code, response.text)
                response.raise_for_status()

            data = response.json()
            used_model = data.get("model", primary)
            logger.info("Response from model: %s", used_model)
            return data

    async def list_models(self) -> list[dict]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/models", headers=headers)
            response.raise_for_status()
            all_models = response.json().get("data", [])
            return [m for m in all_models if ":free" in m.get("id", "") or m.get("pricing", {}).get("prompt") == "0"]
