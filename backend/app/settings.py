# Environment variable setup for email testing and SendGrid:
# export TEST_EMAIL_RECIPIENT=abraham@cognativ.com
# export SENDGRID_API_KEY=your_sendgrid_api_key
# export EMAIL_USER=abraham@cognativ.com
# export EMAIL_HOST=your_verified_domain_or_email_host

import os
from pydantic_settings import BaseSettings
from pydantic import Field, EmailStr
from typing import Optional
from pydantic import ConfigDict

class BaseAppSettings(BaseSettings):
    APP_ENV: str = Field(..., json_schema_extra={"env": "APP_ENV"})
    DB_URL: str = Field(..., json_schema_extra={"env": "DB_URL"})
    EMAIL_HOST: str = Field(..., json_schema_extra={"env": "EMAIL_HOST"})
    EMAIL_PORT: int = Field(..., json_schema_extra={"env": "EMAIL_PORT"})
    EMAIL_USER: Optional[str] = Field(None, json_schema_extra={"env": "EMAIL_USER"})
    EMAIL_PASSWORD: Optional[str] = Field(None, json_schema_extra={"env": "EMAIL_PASSWORD"})
    SECRET_KEY: str = Field(..., json_schema_extra={"env": "SECRET_KEY"})
    SENDGRID_API_KEY: str = Field(..., json_schema_extra={"env": "SENDGRID_API_KEY"})
    REGISTER_URL: str = Field(..., json_schema_extra={"env": "REGISTER_URL"})
    # Add other common settings here

    model_config = ConfigDict(env_file=".env", case_sensitive=True)

class DevelopmentSettings(BaseAppSettings):
    APP_ENV: str = "development"
    DB_URL: str = "postgresql://ogol:qwertyuiop@localhost:5432/leavemanagerone"
    EMAIL_HOST: str = "localhost"
    EMAIL_PORT: int = 1025
    EMAIL_USER: Optional[str] = "info@cognativ.com"
    EMAIL_PASSWORD: Optional[str] = None
    SECRET_KEY: str = "dev-secret-key"
    SENDGRID_API_KEY: str = "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"
    REGISTER_URL: str = "http://localhost:8000/"  # Registration page base URL

class TestingSettings(BaseAppSettings):
    APP_ENV: str = "testing"
    DB_URL: str = "postgresql://ogol:qwertyuiop@localhost:5432/leavemanageronetest"
    EMAIL_HOST: str = "localhost"
    EMAIL_PORT: int = 1025
    EMAIL_USER: Optional[str] = "info@cognativ.com"
    EMAIL_PASSWORD: Optional[str] = None
    SECRET_KEY: str = "test-secret-key"
    SENDGRID_API_KEY: str = "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"
    REGISTER_URL: str = "https://your-app-url/"

class ProductionSettings(BaseAppSettings):
    APP_ENV: str = "production"
    DB_URL: str = "postgresql://ogol:qwertyuiop@localhost:5432/leavemanager"
    EMAIL_HOST: str = Field(..., json_schema_extra={"env": "EMAIL_HOST"})
    EMAIL_PORT: int = Field(..., json_schema_extra={"env": "EMAIL_PORT"})
    EMAIL_USER: Optional[str] = Field("info@cognativ.com", json_schema_extra={"env": "EMAIL_USER"})
    EMAIL_PASSWORD: Optional[str] = Field(None, json_schema_extra={"env": "EMAIL_PASSWORD"})
    SECRET_KEY: str = Field(..., json_schema_extra={"env": "SECRET_KEY"})
    SENDGRID_API_KEY: str = Field(..., json_schema_extra={"env": "SENDGRID_API_KEY"})
    REGISTER_URL: str = Field("https://your-app-url/", json_schema_extra={"env": "REGISTER_URL"})



def get_settings() -> BaseAppSettings:
    env = os.getenv("APP_ENV", "development").lower()
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()
