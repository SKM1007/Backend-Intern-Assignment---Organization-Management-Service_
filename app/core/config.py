from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Use the .env file path relative to the project root
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"

class Settings(BaseSettings):
    # MongoDB Settings
    MONGO_URI: str
    MASTER_DB_NAME: str

    # JWT Settings
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        extra="ignore"
    )

settings = Settings()