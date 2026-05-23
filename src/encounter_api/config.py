"""Application settings, read from the environment with safe local defaults.

Typed settings mean a misconfiguration fails at startup rather than at the first
request. The default secret is obviously a development placeholder; a real
deployment supplies ``ENCOUNTER_API_JWT_SECRET`` (or, per the README, switches
to asymmetric keys entirely).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "local-development-secret-not-for-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ENCOUNTER_API_",
        env_file=".env",
        extra="ignore",
    )

    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "encounter-api"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
