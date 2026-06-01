#!/usr/bin/env python3
"""Add free OpenRouter model YAMLs to Dify plugin and set defaults."""
import json
import subprocess
import textwrap
import uuid

OPENROUTER_KEY = None
PROVIDER = "langgenius/openrouter/openrouter"
TENANT_ID = "a528d4cf-523b-4c2c-809a-2f10bcbbb529"

PLUGIN_BASE = subprocess.check_output(
    "docker exec dify-plugin_daemon-1 find /app/storage/cwd -maxdepth 1 -name 'openrouter-*' -type d",
    shell=True, text=True,
).strip().split("\n")[0]

LLM_DIR = f"{PLUGIN_BASE}/models/llm"

FREE_LLMS = [
    ("meta-llama/llama-3.3-70b-instruct:free", "Llama 3.3 70B Free", 131072),
    ("qwen/qwen3-coder:free", "Qwen3 Coder Free", 1000000),
    ("google/gemma-4-31b-it:free", "Gemma 4 31B Free", 131072),
    ("openai/gpt-oss-20b:free", "GPT-OSS 20B Free", 131072),
    ("z-ai/glm-4.5-air:free", "GLM 4.5 Air Free", 131072),
    ("deepseek/deepseek-r1:free", "DeepSeek R1 Free", 163840),
]

YAML_TEMPLATE = """\
model: {model_id}
label:
  en_US: {label}
  ru_RU: {label}
model_type: llm
features:
  - multi-tool-call
  - agent-thought
  - stream-tool-call
model_properties:
  mode: chat
  context_size: {context}
parameter_rules:
  - name: temperature
    use_template: temperature
  - name: top_p
    use_template: top_p
  - name: max_tokens
    use_template: max_tokens
    default: 4096
    max: 8192
pricing:
  input: "0.0"
  output: "0.0"
  unit: "0.000001"
  currency: USD
"""


def sh(cmd: str) -> str:
    return subprocess.check_output(cmd, shell=True, text=True).strip()


def psql(sql: str) -> None:
    sh(f'docker exec dify-db_postgres-1 psql -U postgres -d dify -c "{sql}"')


def main():
    print(f"Plugin path: {PLUGIN_BASE}")

    for model_id, label, ctx in FREE_LLMS:
        safe_name = model_id.replace("/", "-").replace(":", "-")
        content = YAML_TEMPLATE.format(model_id=model_id, label=label, context=ctx)
        remote_path = f"{LLM_DIR}/{safe_name}.yaml"
        # write via docker exec
        escaped = content.replace("'", "'\\''")
        sh(f"docker exec dify-plugin_daemon-1 sh -c 'cat > {remote_path} << '\"'\"'EOF'\"'\"'\n{content}EOF'")
        print(f"Added {model_id}")

    primary = FREE_LLMS[0][0]

    # System LLM = first free model
    psql(
        f"UPDATE tenant_default_models SET provider_name='{PROVIDER}', "
        f"model_name='{primary}', updated_at=NOW() "
        f"WHERE tenant_id='{TENANT_ID}' AND model_type='llm';"
    )

    # Remove paid embedding default — use RAGFlow for knowledge base instead
    psql(
        f"DELETE FROM tenant_default_models WHERE tenant_id='{TENANT_ID}' "
        f"AND model_type='text-embedding';"
    )

    # Enable only free models in settings
    paid_models = [
        "openrouter/auto", "gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-3.5-turbo",
        "gpt-5", "gpt-5.1", "o3-mini", "openai/text-embedding-3-large",
        "openai/text-embedding-3-small",
    ]
    for model in paid_models:
        psql(
            f"INSERT INTO provider_model_settings (id, tenant_id, provider_name, model_name, model_type, enabled, load_balancing_enabled) "
            f"VALUES ('{uuid.uuid4()}', '{TENANT_ID}', '{PROVIDER}', '{model}', 'llm', false, false) "
            f"ON CONFLICT DO NOTHING;"
        )

    for model_id, _, _ in FREE_LLMS:
        psql(
            f"INSERT INTO provider_model_settings (id, tenant_id, provider_name, model_name, model_type, enabled, load_balancing_enabled) "
            f"VALUES ('{uuid.uuid4()}', '{TENANT_ID}', '{PROVIDER}', '{model_id}', 'llm', true, false) "
            f"ON CONFLICT DO NOTHING;"
        )

    sh("docker restart dify-plugin_daemon-1 dify-api-1 dify-worker-1 dify-web-1")
    print(f"Primary LLM: {primary}")
    print("Embedding removed — use RAGFlow for knowledge base (rag.siteaacess.ru)")
    print("Restart complete")


if __name__ == "__main__":
    main()
