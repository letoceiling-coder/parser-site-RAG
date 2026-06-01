#!/usr/bin/env python3
"""Disable all paid OpenRouter models in Dify, enable only FREE-* models."""
import subprocess
import uuid

TENANT_ID = "a528d4cf-523b-4c2c-809a-2f10bcbbb529"
PROVIDER = "langgenius/openrouter/openrouter"
PRIMARY = "meta-llama/llama-3.3-70b-instruct:free"

PLUGIN_DIR = subprocess.check_output(
    "docker exec dify-plugin_daemon-1 find /app/storage/cwd/langgenius -maxdepth 1 -name 'openrouter-*' -type d",
    shell=True, text=True,
).strip().split("\n")[0]
LLM_DIR = f"{PLUGIN_DIR}/models/llm"


def sh(cmd: str) -> str:
    return subprocess.check_output(cmd, shell=True, text=True).strip()


def psql(sql: str) -> None:
    sh(f'docker exec dify-db_postgres-1 psql -U postgres -d dify -q -c "{sql}"')


def get_models() -> list[tuple[str, str, bool]]:
    """Return (model_id, filename, is_free) for each yaml."""
    files = sh(f'docker exec dify-plugin_daemon-1 ls {LLM_DIR}').split()
    result = []
    for fname in files:
        if not fname.endswith(".yaml"):
            continue
        path = f"{LLM_DIR}/{fname}"
        line = sh(f"docker exec dify-plugin_daemon-1 grep '^model:' {path} | head -1")
        model = line.replace("model:", "", 1).strip().strip('"').strip("'")
        is_free = fname.startswith("free-") or ":free" in model
        result.append((model, fname, is_free))
    return result


def main():
    models = get_models()
    print(f"Found {len(models)} models, {sum(1 for _, _, f in models if f)} free")

    psql(f"DELETE FROM provider_model_settings WHERE tenant_id='{TENANT_ID}' AND provider_name='{PROVIDER}';")

    for model_id, fname, is_free in models:
        enabled = "true" if is_free else "false"
        mid = model_id.replace("'", "''")
        psql(
            f"INSERT INTO provider_model_settings (id, tenant_id, provider_name, model_name, model_type, enabled, load_balancing_enabled) "
            f"VALUES ('{uuid.uuid4()}', '{TENANT_ID}', '{PROVIDER}', '{mid}', 'llm', {enabled}, false);"
        )

    psql(
        f"UPDATE tenant_default_models SET provider_name='{PROVIDER}', model_name='{PRIMARY}', updated_at=NOW() "
        f"WHERE tenant_id='{TENANT_ID}' AND model_type='llm';"
    )
    psql(f"DELETE FROM tenant_default_models WHERE tenant_id='{TENANT_ID}' AND model_type='text-embedding';")

    sh("docker restart dify-plugin_daemon-1 dify-api-1 dify-worker-1 dify-web-1")
    print(f"Done. Default: {PRIMARY}")
    print("Search 'FREE' in Dify model picker")


if __name__ == "__main__":
    main()
