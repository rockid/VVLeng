"""LLM client wrapper — laozhang.ai via OpenAI-compatible API."""

import os
import logging
from pathlib import Path

from openai import OpenAI

logger = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompts"

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Lazy-initialised OpenAI client pointed at laozhang.ai."""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ["LAOZHANG_API_KEY"],
            base_url=os.environ["LAOZHANG_BASE_URL"],
        )
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
) -> str:
    """
    Call laozhang.ai (OpenAI-compatible) and return the response text.

    Args:
        prompt: User message content.
        system: System message content.
        model: Model name (falls back to LLM_DEFAULT_MODEL env var).
        max_tokens: Maximum tokens in response.
        temperature: Sampling temperature (0.0–2.0).

    Returns:
        The model's response text, stripped.
    """
    model = model or os.getenv("LLM_DEFAULT_MODEL", "gpt-4o-mini")
    client = _get_client()

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