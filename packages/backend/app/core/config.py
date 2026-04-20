from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://pranely:changeme@localhost:5432/pranely_dev"
    redis_url: str = "redis://localhost:6379"
    debug: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
