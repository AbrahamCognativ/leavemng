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
    SITE_URL: str
    DDB_URL: str
    UPLOAD_DIR: str = "/app/api/uploads"

    class Config:
        env_file = ".env.prod"
        # pass  # Do not set env_file; rely on environment variables


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
    SITE_URL: str
    DDB_URL: str
    UPLOAD_DIR: str = "/app/api/uploads"

    class Config:
        env_file = ".env.dev"
        # pass  # Do not set env_file; rely on environment variables


def get_settings():
    import os
    env = os.getenv("APP_ENV", "development")
    if env == "production":
        return ProductionSettings()
    return DevelopmentSettings()
