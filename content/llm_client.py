"""LLM client wrapper — laozhang.ai via OpenAI-compatible API."""

import os
import logging
from pathlib import Path
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompts"

_client: OpenAI | None = None
_last_config = None  # track last config used for lazy init


def _get_client(config: Optional[object] = None) -> OpenAI:
    """Lazy-initialised OpenAI client pointed at laozhang.ai."""
    global _client, _last_config

    # Determine API key and base URL
    if config and hasattr(config, "llm"):
        api_key = getattr(config.llm, "api_key", "") or os.environ.get("LLM_API_KEY", "")
        base_url = getattr(config.llm, "base_url", "") or os.environ.get("LLM_BASE_URL", "https://api.laozhang.ai/v1")
    else:
        # Fallback to old env var names for backwards compatibility
        api_key = os.environ.get("LLM_API_KEY", os.environ.get("LAOZHANG_API_KEY", ""))
        base_url = os.environ.get("LLM_BASE_URL", os.environ.get("LAOZHANG_BASE_URL", "https://api.laozhang.ai/v1"))

    # Re-init if config changed (different client)
    if _client is None or _last_config != f"{api_key}:{base_url}":
        _client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        _last_config = f"{api_key}:{base_url}"
    return _client


def load_prompt(name: str) -> str:
    """Load a prompt text file from content/prompts/."""
    path = PROMPT_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def complete(
    prompt: str,
    system: str,
    model: str | None = None,
    max_tokens: int = 500,
    temperature: float = 0.7,
    config: Optional[object] = None,
) -> str:
    """
    Call laozhang.ai (OpenAI-compatible) and return the response text.

    Args:
        prompt: User message content.
        system: System message content.
        model: Model name (falls back to config.llm.comment_model, then env var).
        max_tokens: Maximum tokens in response.
        temperature: Sampling temperature (0.0–2.0).
        config: Optional AppConfig object (for model names and credentials).

    Returns:
        The model's response text, stripped.
    """
    # Determine model: explicit arg → config → env → default
    if model is None:
        if config and hasattr(config, "llm") and hasattr(config.llm, "comment_model"):
            model = config.llm.comment_model
        else:
            model = os.getenv("LLM_DEFAULT_MODEL", "gpt-4o-mini")

    client = _get_client(config)

    logger.info("LLM call — model=%s, max_tokens=%d, temperature=%.1f", model, max_tokens, temperature)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    text = response.choices[0].message.content.strip()
    logger.info("LLM response received (%d chars)", len(text))
    return text