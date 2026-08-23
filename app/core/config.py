import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "SCAMCHECK"
    DATABASE_URL: str = "sqlite:///./scamcheck.db"
    REDIS_URL: str | None = None
    
    # ML model configurations
    NLP_MODEL_PATH: str | None = None
    URL_MODEL_PATH: str | None = None
    FUSION_MODEL_PATH: str | None = None
    
    # Fallback/override to enforce demo mode
    FORCE_DEMO_MODE: bool = False
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
