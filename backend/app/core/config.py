from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str

    # Redis
    redis_url: str

    # API
    secret_key: str
    superadmin_password: str
    superadmin_email: str = "admin@forenteplaneter.no"
    environment: str = "development"

    # JWT
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    invite_token_expire_days: int = 7
    email_verify_token_expire_hours: int = 24

    # SMTP
    smtp_host: str = "mail.smtp2go.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@forenteplaneter.no"
    smtp_from_name: str = "Forente Planeter"

    # Game
    game_name: str = "Forente Planeter"
    game_base_url: str = "http://localhost:5173"
    invites_per_player: int = 100
    invite_reward_metal: int = 10000
    invite_reward_energy: int = 10000
    invite_reward_gas: int = 10000

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
