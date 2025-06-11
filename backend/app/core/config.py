from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    class Config:
        # Build a robust path to the .env file, assuming it's in the 'backend' directory
        # __file__ -> backend/app/core/config.py
        # .parent -> backend/app/core
        # .parent.parent -> backend/app
        # .parent.parent.parent -> backend
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        env_file = env_path
        env_file_encoding = "utf-8"
    PROJECT_NAME: str = "Physiological Signal Monitoring and Analysis System"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/physio_monitoring"

    # JWT
    SECRET_KEY: str = "a_very_secret_key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8 # 8 days
    JWT_ALGORITHM: str = "HS256"

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
