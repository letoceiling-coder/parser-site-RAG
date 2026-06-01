#!/usr/bin/env python3
"""Configure Dify to use only free OpenRouter models."""
import json
import subprocess
import urllib.request

import os

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
PROVIDER = "langgenius/openrouter/openrouter"
TENANT_ID = "a528d4cf-523b-4c2c-809a-2f10bcbbb529"

# Free LLM models (priority order)
FREE_LLMS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "qwen/qwen3-4b:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "deepseek/deepseek-r1:free",
]

# Cheapest embedding on OpenRouter (small, low cost; for fully free use RAGFlow)
FREE_EMBEDDING = "openai/text-embedding-3-small"


def fetch_openrouter_free():
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    free = []
    for m in data.get("data", []):
        mid = m.get("id", "")
        pricing = m.get("pricing") or {}
        if ":free" in mid or pricing.get("prompt") in ("0", 0, "0.0"):
            free.append(mid)
    return free


def psql(sql: str) -> str:
    cmd = [
        "docker", "exec", "dify-db_postgres-1",
        "psql", "-U", "postgres", "-d", "dify", "-t", "-A", "-c", sql,
    ]
    return subprocess.check_output(cmd, text=True).strip()


def main():
    available = set(fetch_openrouter_free())
    print(f"OpenRouter free models available: {len(available)}")

    llm = next((m for m in FREE_LLMS if m in available), None)
    if not llm:
        # fallback: any :free llm
        llm = next((m for m in available if ":free" in m and "embed" not in m.lower()), "meta-llama/llama-3.3-70b-instruct:free")
    print(f"Selected LLM: {llm}")

    embedding = FREE_EMBEDDING
    if embedding not in available:
        embedding = next((m for m in available if "embed" in m.lower()), FREE_EMBEDDING)
    print(f"Selected embedding: {embedding}")

    # Update tenant default models
    for model_type, model_name in [("llm", llm), ("text-embedding", embedding)]:
        exists = psql(
            f"SELECT id FROM tenant_default_models WHERE tenant_id='{TENANT_ID}' AND model_type='{model_type}';"
        )
        if exists:
            psql(
                f"UPDATE tenant_default_models SET provider_name='{PROVIDER}', model_name='{model_name}', updated_at=NOW() "
                f"WHERE tenant_id='{TENANT_ID}' AND model_type='{model_type}';"
            )
        else:
            psql(
                f"INSERT INTO tenant_default_models (id, tenant_id, provider_name, model_name, model_type, created_at, updated_at) "
                f"VALUES (gen_random_uuid(), '{TENANT_ID}', '{PROVIDER}', '{model_name}', '{model_type}', NOW(), NOW());"
            )
        print(f"Updated default {model_type} -> {model_name}")

    # Disable paid models in provider_model_settings if table used
    try:
        psql(
            f"DELETE FROM tenant_default_models WHERE tenant_id='{TENANT_ID}' AND model_name IN "
            f"('openrouter/auto', 'openai/text-embedding-3-large', 'gpt-4o', 'gpt-4o-mini');"
        )
    except Exception:
        pass

    print("Done. Restart Dify web cache if needed.")


if __name__ == "__main__":
    main()
