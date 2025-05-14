from pydantic_settings import BaseSettings

class ProductionSettings(BaseSettings):
    APP_ENV: str
    DB_URL: str
    EMAIL_HOST: str
    EMAIL_PORT: int
    EMAIL_USER: str
    EMAIL_PASSWORD: str
    SECRET_KEY: str
    SENDGRID_API_KEY: str
    REGISTER_URL: str
    UPLOAD_DIR: str = "/app/api/uploads"

    class Config:
        env_file = ".env.prod"

class DevelopmentSettings(BaseSettings):
    APP_ENV: str
    DB_URL: str
    EMAIL_HOST: str
    EMAIL_PORT: int
    EMAIL_USER: str
    EMAIL_PASSWORD: str
    SECRET_KEY: str
    SENDGRID_API_KEY: str
    REGISTER_URL: str
    UPLOAD_DIR: str = "/app/api/uploads"

    class Config:
        env_file = ".env.dev"


def get_settings():
    import os
    env = os.getenv("APP_ENV", "development").lower()
    if env == "production":
        return ProductionSettings()
    else:
        return DevelopmentSettings()
