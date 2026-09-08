from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://vortexia:vortexia@db:5432/vortexia"
    redis_url: str = "redis://redis:6379/0"

    openai_api_key: str = ""
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    admin_api_key: str = ""
    ip_salt: str = ""

    demo_domain: str = "demo.getvortexia.com"  # {tenant}.{demo_domain}


settings = Settings()
