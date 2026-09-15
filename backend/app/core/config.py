import os
from pathlib import Path
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/project_tracking"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    UPLOAD_MAX_SIZE: int = 52428800  # 50MB
    STORAGE_PATH: str = "./storage/uploads"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    TOKEN_EXPIRE_MINUTES: int = 720  # 12 hours
    ADMIN_REGISTRATION_SECRET: str = ""
    DEFAULT_PROJECT_NAME: str = "MOLA FAKO Construction Project"
    ASSISTANT_PROVIDER: str = "openai"  # "openai" or "deterministic"
    OPENAI_API_KEY: SecretStr = SecretStr("")
    OPENAI_MODEL: str = "gpt-4o-mini"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def openai_api_key(self) -> str:
        return self.OPENAI_API_KEY.get_secret_value()

    @model_validator(mode="after")
    def _reject_well_known_secret_outside_development(self):
        if (
            self.ENVIRONMENT != "development"
            and self.SECRET_KEY == "dev-secret-key-change-in-production"
        ):
            raise ValueError(
                "SECRET_KEY must be set to a strong random value when ENVIRONMENT is not 'development'."
            )
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

Path(settings.STORAGE_PATH).mkdir(parents=True, exist_ok=True)
