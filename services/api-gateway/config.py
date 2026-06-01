from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    domain: str = "siteaacess.ru"

    s3_endpoint: str = ""
    s3_region: str = "ru-3"
    s3_bucket: str = "knowledge-raw"
    s3_access_key: str = ""
    s3_secret_key: str = ""

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "parser"
    postgres_password: str = ""
    postgres_db: str = "parser_rag"

    redis_host: str = "redis"
    redis_password: str = ""

    ragflow_url: str = "http://localhost:9380"
    dify_url: str = "http://localhost:8081"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
