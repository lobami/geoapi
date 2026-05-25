from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "GeoAPI Geospatial Platform"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/geoapi"
    allowed_origins: str = "http://localhost:5173"
    fyra_api_key: str | None = None
    fyra_base_url: str = "https://api.fyra.im/v1"
    fyra_model: str = "gpt-oss-20b"
    jwt_secret: str = "geoapi-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
