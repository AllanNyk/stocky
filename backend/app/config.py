from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./stocky.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    initial_mock_cash: float = 100_000.0
    cors_origins: str = "http://localhost:5173"

    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "stocky-local/0.1"

    finnhub_api_key: str = ""
    admin_token: str = ""
    invite_code: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def reddit_enabled(self) -> bool:
        return bool(self.reddit_client_id and self.reddit_client_secret)

    @property
    def finnhub_enabled(self) -> bool:
        return bool(self.finnhub_api_key)

    @property
    def admin_enforced(self) -> bool:
        return bool(self.admin_token)

    @property
    def invite_required(self) -> bool:
        return bool(self.invite_code)


settings = Settings()
