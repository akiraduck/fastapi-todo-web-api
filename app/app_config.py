import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Currency Exchange API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    DATABASE_URL: str = "sqlite+aiosqlite:///./currency.db"

    NATS_URL: str = os.getenv("NATS_URL", "nats://localhost:4222")

    BACKGROUND_TASK_INTERVAL: int = 60

    WS_SEND_TIMEOUT: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

settings = Settings()
