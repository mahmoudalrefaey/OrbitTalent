"""Application settings, loaded from environment / .env file."""
from functools import lru_cache
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- LLM provider -------------------------------------------------------
    # Key comes from env ONLY — never hardcode a secret in source.
    # `llm_api_key` is preferred; `anthropic_api_key` is accepted for
    # backwards-compat with the V1 .env and tests.
    llm_api_key: str = ""
    anthropic_api_key: str = ""

    # OpenAI-compatible endpoint on g0i.ai (chosen for cost). The OpenAI SDK
    # expects the URL to include the /v1 path. Override per-environment.
    llm_base_url: str = "https://api.g0i.ai/v1"

    # Models — overridable via env to match whatever your g0i.ai plan allows.
    # Defaults are placeholders; set MODEL_DEEP / MODEL_CHEAP in .env to ids
    # your plan actually permits (e.g. qwen3-coder-80b).
    model_deep: str = "qwen3-coder-80b"
    model_cheap: str = "qwen3-coder-80b"
    # Empty disables the embedding pre-filter tier (graceful degradation when
    # the provider has no embeddings endpoint).
    model_embed: str = ""

    # Comma-separated fallback models tried (in order) when the primary model
    # errors (e.g. plan/availability errors).
    fallback_models: str = ""

    database_url: str = "sqlite:///./orbittalent.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Auth ---------------------------------------------------------------
    # Secret used to sign session JWTs. MUST be set in production via env.
    # The insecure dev default triggers a loud warning (see get_settings).
    jwt_secret: str = "dev-insecure-change-me"
    jwt_expire_days: int = 7
    # Set true when serving over HTTPS so the session cookie gets `Secure`.
    cookie_secure: bool = False

    # --- Cascade tuning -----------------------------------------------------
    # Below this keyword coverage of required skills, exit at Tier 0 (free).
    tier0_min_coverage: float = 0.05
    # Cosine threshold for the optional embedding gate (Tier 1).
    tier1_min_similarity: float = 0.20
    # Accept the cheap Tier-2 score (skip the expensive Tier 3) at/above this
    # self-reported confidence.
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
    price_embed_input: float = 0.02

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
        """Return {input, output, cached} $/Mtok for a model name."""
        if model == self.model_deep:
            return {
                "input": self.price_deep_input,
                "output": self.price_deep_output,
                "cached": self.price_deep_cached,
            }
        if model == self.model_embed:
            return {"input": self.price_embed_input, "output": 0.0, "cached": 0.0}
        # Default to cheap-model pricing.
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
