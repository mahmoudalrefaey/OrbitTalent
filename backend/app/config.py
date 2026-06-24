"""Application settings, loaded from environment / .env file."""
from functools import lru_cache
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- LLM provider -------------------------------------------------------
    # API key from the environment. `anthropic_api_key` is kept as a fallback
    # name so older .env files keep working.
    llm_api_key: str = ""
    anthropic_api_key: str = ""

    # g0i.ai OpenAI-compatible endpoint. The SDK needs the /v1 suffix.
    llm_base_url: str = "https://api.g0i.ai/v1"

    # Model ids must be ones the g0i.ai plan allows; override per-environment.
    model_deep: str = "gpt-4o"
    model_cheap: str = "gpt-4o-mini"

    # Fallback models (comma-separated), tried in order if the primary errors.
    fallback_models: str = ""

    # PostgreSQL connection URL, e.g.
    # postgresql+psycopg://user:password@localhost:5432/orbittalent
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/orbittalent"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Auth ---------------------------------------------------------------
    # JWT signing secret. The dev default is insecure and logs a warning on
    # startup; set a real value in production.
    jwt_secret: str = "dev-insecure-change-me"
    jwt_expire_days: int = 7
    cookie_secure: bool = False  # set true behind HTTPS for the Secure flag

    # Per-IP rate limiting on sensitive endpoints (auth). Disabled in tests.
    rate_limit_enabled: bool = True

    # --- Upload limits ------------------------------------------------------
    # Max CV uploads per user (== per tenant; users are 1:1 with tenants) in a
    # rolling 24h window, and the max size of a single uploaded file.
    daily_upload_limit: int = 20
    max_upload_mb: int = 2

    # --- Cascade tuning -----------------------------------------------------
    # Minimum required-skill keyword coverage to clear Tier 0.
    tier0_min_coverage: float = 0.05
    # Tier-1 lexical similarity threshold (BM25 + weighted skill overlap, scored
    # 0-100, compared against this * 100). 0.35 is a moderate gate: clearly weak
    # CVs are filtered before any LLM cost, decent matches pass through.
    tier1_min_similarity: float = 0.35
    # Confidence at/above which the cheap Tier-2 score is accepted as final.
    tier2_accept_confidence: float = 0.75
    # Tier-2 match% at/above which we still escalate to Tier 3 for a precise
    # overall score on strong candidates, even if confidence was high.
    tier3_escalate_match_pct: float = 70.0

    # --- Pricing (USD per 1M tokens) ---------------------------------------
    # Used for cost estimation/logging. Override via env for the real provider.
    price_deep_input: float = 15.0
    price_deep_output: float = 75.0
    price_deep_cached: float = 1.5
    price_cheap_input: float = 1.0
    price_cheap_output: float = 5.0
    price_cheap_cached: float = 0.1

    @property
    def api_key(self) -> str:
        return self.llm_api_key or self.anthropic_api_key

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def fallback_model_list(self) -> list[str]:
        return [m.strip() for m in self.fallback_models.split(",") if m.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.api_key)

    @property
    def provider(self) -> str:
        """Human-readable provider host, derived from the base URL."""
        host = urlparse(self.llm_base_url).netloc or self.llm_base_url
        return host

    def price_for(self, model: str) -> dict[str, float]:
        """Per-1M-token {input, output, cached} pricing for a model."""
        if model == self.model_deep:
            return {
                "input": self.price_deep_input,
                "output": self.price_deep_output,
                "cached": self.price_deep_cached,
            }
        return {
            "input": self.price_cheap_input,
            "output": self.price_cheap_output,
            "cached": self.price_cheap_cached,
        }


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.jwt_secret == "dev-insecure-change-me":
        import logging

        logging.getLogger("orbittalent").warning(
            "JWT_SECRET is using the insecure dev default. Set JWT_SECRET in the "
            "environment before deploying — sessions are forgeable otherwise."
        )
    return settings
