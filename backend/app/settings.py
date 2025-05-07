import os
from pydantic_settings import BaseSettings
from pydantic import Field, EmailStr
from typing import Optional

class BaseAppSettings(BaseSettings):
    APP_ENV: str = Field(..., env="APP_ENV")
    DB_URL: str = Field(..., env="DB_URL")
    EMAIL_HOST: str = Field(..., env="EMAIL_HOST")
    EMAIL_PORT: int = Field(..., env="EMAIL_PORT")
    EMAIL_USER: Optional[str] = Field(None, env="EMAIL_USER")
    EMAIL_PASSWORD: Optional[str] = Field(None, env="EMAIL_PASSWORD")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    # Add other common settings here

    class Config:
        env_file = ".env"
        case_sensitive = True

class DevelopmentSettings(BaseAppSettings):
    APP_ENV: str = "development"
    DB_URL: str = "postgresql://ogol:qwertyuiop@localhost:5432/leavemanagerone"
    EMAIL_HOST: str = "localhost"
    EMAIL_PORT: int = 1025
    EMAIL_USER: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    SECRET_KEY: str = "dev-secret-key"

class TestingSettings(BaseAppSettings):
    APP_ENV: str = "testing"
    DB_URL: str = "postgresql://ogol:qwertyuiop@localhost:5432/leavemanageronetest"
    EMAIL_HOST: str = "localhost"
    EMAIL_PORT: int = 1025
    EMAIL_USER: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    SECRET_KEY: str = "test-secret-key"

class ProductionSettings(BaseAppSettings):
    APP_ENV: str = "production"
    DB_URL: str = "postgresql://ogol:qwertyuiop@localhost:5432/leavemanager"
    EMAIL_HOST: str = Field(..., env="EMAIL_HOST")
    EMAIL_PORT: int = Field(..., env="EMAIL_PORT")
    EMAIL_USER: Optional[str] = Field(None, env="EMAIL_USER")
    EMAIL_PASSWORD: Optional[str] = Field(None, env="EMAIL_PASSWORD")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")


def get_settings() -> BaseAppSettings:
    env = os.getenv("APP_ENV", "development").lower()
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()
