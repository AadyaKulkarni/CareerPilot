from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Placement Readiness & Career Intelligence Portal"
    environment: str = "development"
    secret_key: str = "change-me"
    jwt_expire_minutes: int = 1440
    backend_cors_origins: str = "http://localhost:5173"
    database_url: str = "sqlite:///./career_portal.db"
    redis_url: str = "redis://localhost:6379/0"
    llm_provider: str = "none"
    llm_model: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
