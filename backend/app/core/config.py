from pydantic import BaseSettings

class Settings(BaseSettings):
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
