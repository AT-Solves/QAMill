"""
QAMill Configuration - Zero hardcoded values
All configuration from environment variables via Pydantic
"""
from typing import Dict, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class DatabaseSettings(BaseSettings):
    """Database configuration"""
    url: str = "sqlite:///./qamill.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20

    class Config:
        env_prefix = "DATABASE_"


class AuthSettings(BaseSettings):
    """Authentication configuration"""
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    class Config:
        env_prefix = "AUTH_"


class LLMSettings(BaseSettings):
    """LLM Provider configuration"""
    default_provider: str = "ollama"
    claude_api_key: str = ""
    gpt_api_key: str = ""
    gemini_api_key: str = ""
    grok_api_key: str = ""

    # Model selections per provider
    models: Dict[str, str] = {
        "claude": "claude-sonnet-4-5",
        "gpt": "gpt-4o",
        "gemini": "gemini-2.0-flash",
        "grok": "grok-3",
        "ollama": "llama3",
    }

    class Config:
        env_prefix = "LLM_"


class StorageSettings(BaseSettings):
    """File storage configuration"""
    type: str = "local"  # local, s3
    local_path: str = "./storage"
    s3_bucket: str = ""
    s3_region: str = "us-east-1"

    class Config:
        env_prefix = "STORAGE_"


class OAuthSettings(BaseSettings):
    """OAuth Provider configuration"""
    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:5173/auth/github/callback"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:5173/auth/google/callback"

    class Config:
        env_prefix = "OAUTH_"


class APISettings(BaseSettings):
    """API configuration"""
    host: str = "0.0.0.0"
    port: int = 8765
    debug: bool = False
    reload: bool = False
    workers: int = 1

    class Config:
        env_prefix = "API_"


class AppSettings(BaseSettings):
    """Main application settings"""
    app_name: str = "QAMill AI QA Governance"
    app_version: str = "1.2.0"
    environment: str = "development"  # development, staging, production

    # Sub-settings
    database: DatabaseSettings = DatabaseSettings()
    auth: AuthSettings = AuthSettings()
    llm: LLMSettings = LLMSettings()
    storage: StorageSettings = StorageSettings()
    oauth: OAuthSettings = OAuthSettings()
    api: APISettings = APISettings()

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> AppSettings:
    """Get cached settings instance"""
    return AppSettings()


# Export settings
settings = get_settings()
