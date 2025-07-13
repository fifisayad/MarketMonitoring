from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_reload: bool = False
    app_loop: str = "uvloop"

    class Config:
        env_file = ".env"


settings = Settings()
