from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# load .env into process environment so BaseSettings picks values when instantiated
load_dotenv()


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://trader:trader@postgres:5432/trading"
    redis_url: str = "redis://redis:6379/0"
    trading_mode: str = "PAPER"
    ollama_url: str = "http://localhost:11434/api"
    ollama_model: str = "llama3.2:latest"
    ollama_timeout_seconds: int = 30
    ai_provider: str = "ollama"
    groq_url: str = "https://api.groq.com/openai/v1"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_temperature: float = 1.0
    groq_max_completion_tokens: int = 2048
    groq_top_p: float = 1.0
    groq_reasoning_effort: str = "medium"
    # single bearer token for simple API access control (set via API_BEARER_TOKEN env var)
    api_bearer_token: str | None = None
    # support multiple static bearer tokens (comma-separated in env) or JWT mode
    api_bearer_tokens: list[str] | None = None
    api_auth_mode: str = "simple"  # 'simple' or 'jwt'
    # JWT settings (when api_auth_mode=jwt)
    jwt_secret: str | None = None
    jwt_alg: str = "HS256"
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    # simple admin credentials for login endpoint (set in .env)
    admin_username: str = "admin"
    admin_password: str | None = None
    # simple normal user credentials (optional, for dev)
    user_username: str = "user"
    user_password: str | None = None
    # JWT expiration for issued tokens (seconds)
    jwt_exp_seconds: int = 3600

    model_config = {"extra": "ignore"}

settings = Settings()
