from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "deepseek").strip().lower()
    llm_api_key: str = os.getenv("LLM_API_KEY", "").strip()
    llm_model_id: str = os.getenv("LLM_MODEL_ID", "deepseek-chat").strip()
    llm_base_url: str = os.getenv("LLM_BASE_URL", "").strip()
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "").strip()
    max_tasks: int = int(os.getenv("MAX_TASKS", "4"))
    max_search_results: int = int(os.getenv("MAX_SEARCH_RESULTS", "4"))


def get_settings() -> Settings:
    return Settings()
