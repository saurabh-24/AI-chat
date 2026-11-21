import os
from dataclasses import dataclass
from typing import List


@dataclass
class KeyEntry:
    key_id: str
    api_key: str


class Settings:
    def __init__(self) -> None:
        raw_keys = os.getenv("LLM_API_KEYS", "")
        keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        self.key_pool: List[KeyEntry] = [
            KeyEntry(key_id=f"key_{i + 1}", api_key=k) for i, k in enumerate(keys)
        ]
        self.llm_model: str = os.getenv("LLM_MODEL", "gemini/gemini-flash-lite-latest")
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:////data/app.db")
        self.allowed_origins: List[str] = [
            o.strip()
            for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
            if o.strip()
        ]
        self.enable_failure_simulation: bool = (
            os.getenv("ENABLE_FAILURE_SIMULATION", "false").lower() == "true"
        )
        self.cache_enabled: bool = (
            os.getenv("CACHE_ENABLED", "true").lower() == "true"
        )
        self.default_system_prompt: str = os.getenv(
            "DEFAULT_SYSTEM_PROMPT", "You are a helpful AI assistant."
        )


settings = Settings()