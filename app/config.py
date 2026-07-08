from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://gmaps:gmaps_dev@localhost:5433/gmaps_leads"
    )

    # Politeness — see SOUL.md; these are limits, not suggestions
    scrape_delay_min_s: float = 3.0
    scrape_delay_max_s: float = 8.0
    scrape_daily_cap: int = 400
    scrape_cooldown_hours: int = 6
    scrape_headless: bool = False

    # LLM (phase 6) — OpenAI-compatible endpoint (GLM/Z.ai)
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""


settings = Settings()
