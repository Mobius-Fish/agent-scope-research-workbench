from __future__ import annotations

import os
from typing import Any

from .config import get_settings


def get_chat_model(temperature: float = 0.2) -> Any:
    """
    Build a chat model from environment variables.

    Supported modes:
    - LLM_PROVIDER=deepseek: uses langchain-deepseek ChatDeepSeek
    - LLM_PROVIDER=openai: uses langchain-openai ChatOpenAI
    - LLM_PROVIDER=openai_compatible: uses ChatOpenAI with base_url
    """

    settings = get_settings()

    if not settings.llm_api_key:
        raise RuntimeError(
            "LLM_API_KEY is empty. Copy .env.example to .env and set your model API key."
        )

    if settings.llm_provider == "deepseek":
        os.environ.setdefault("DEEPSEEK_API_KEY", settings.llm_api_key)
        from langchain_deepseek import ChatDeepSeek

        return ChatDeepSeek(model=settings.llm_model_id, temperature=temperature)

    if settings.llm_provider == "openai":
        os.environ.setdefault("OPENAI_API_KEY", settings.llm_api_key)
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.llm_model_id, temperature=temperature)

    if settings.llm_provider == "openai_compatible":
        if not settings.llm_base_url:
            raise RuntimeError("LLM_BASE_URL is required for LLM_PROVIDER=openai_compatible.")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model_id,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=temperature,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER={settings.llm_provider!r}. "
        "Use deepseek, openai, or openai_compatible."
    )
