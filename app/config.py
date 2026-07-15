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

    # LLM (phase 6) — vendor-neutral. Two wire formats are supported by
    # app.scoring.llm: "anthropic" (Z.ai coding-plan key) and "openai"
    # (OpenAI-compatible servers, incl. self-hosted vLLM/Qwen). No hardcoded
    # vendor; everything is config-driven per CLAUDE.md.
    llm_api_format: str = "anthropic"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""


settings = Settings()


# --- Live-overridable runtime config (env defaults <- DB overrides) ---------

def get_runtime_config() -> dict:
    """Merge .env scrape defaults with any DB-stored overrides (runtime_config).

    DB is the source of truth for live values edited from the Settings tab so
    that changes apply to the next job without a restart. Falls back to the
    ``settings`` defaults whenever the DB row is absent or the DB is unreachable.
    """
    defaults = {
        "scrape_delay_min_s": settings.scrape_delay_min_s,
        "scrape_delay_max_s": settings.scrape_delay_max_s,
        "scrape_daily_cap": settings.scrape_daily_cap,
    }
    try:
        from sqlalchemy import select

        from app.db.models import RuntimeConfig
        from app.db.session import SessionLocal

        with SessionLocal() as session:
            row = session.get(RuntimeConfig, 1)
        if row is not None:
            defaults.update(
                {
                    "scrape_delay_min_s": row.scrape_delay_min_s,
                    "scrape_delay_max_s": row.scrape_delay_max_s,
                    "scrape_daily_cap": row.scrape_daily_cap,
                }
            )
    except Exception:
        # DB not ready (e.g. before migrations run) — env defaults are fine.
        pass
    return defaults


def update_runtime_config(
    scrape_delay_min_s: float | None = None,
    scrape_delay_max_s: float | None = None,
    scrape_daily_cap: int | None = None,
) -> dict:
    """Persist live knob overrides. Returns the new merged config."""
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert

    from app.db.models import RuntimeConfig
    from app.db.session import SessionLocal

    current = get_runtime_config()
    new_vals = {
        "scrape_delay_min_s": scrape_delay_min_s
        if scrape_delay_min_s is not None
        else current["scrape_delay_min_s"],
        "scrape_delay_max_s": scrape_delay_max_s
        if scrape_delay_max_s is not None
        else current["scrape_delay_max_s"],
        "scrape_daily_cap": scrape_daily_cap
        if scrape_daily_cap is not None
        else current["scrape_daily_cap"],
    }
    # keep max >= min so polite_delay never inverts
    if new_vals["scrape_delay_max_s"] < new_vals["scrape_delay_min_s"]:
        new_vals["scrape_delay_max_s"] = new_vals["scrape_delay_min_s"]

    stmt = (
        insert(RuntimeConfig)
        .values(id=1, **new_vals)
        .on_conflict_do_update(
            index_elements=[RuntimeConfig.id],
            set_={
                "scrape_delay_min_s": new_vals["scrape_delay_min_s"],
                "scrape_delay_max_s": new_vals["scrape_delay_max_s"],
                "scrape_daily_cap": new_vals["scrape_daily_cap"],
            },
        )
    )
    with SessionLocal() as session:
        session.execute(stmt)
        session.commit()
    return new_vals
