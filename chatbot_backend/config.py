import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_file() -> None:
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.exists():
        return

    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip()


_load_env_file()


@dataclass
class Settings:
    app_name: str = os.getenv("APP_NAME", "chatbot-backend")
    app_env: str = os.getenv("APP_ENV", "dev")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    odoo_url: str = os.getenv("ODOO_URL", "http://localhost:8069")
    odoo_db: str = os.getenv("ODOO_DB", "odoo19_dev")
    odoo_login: str = os.getenv("ODOO_LOGIN", "")
    odoo_api_key: str = os.getenv("ODOO_API_KEY", "")

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")


def get_settings() -> Settings:
    return Settings()
