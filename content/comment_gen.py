"""Comment generation — LLM-powered with guardrails."""

import os
import re
import logging
from typing import Any

from .llm_client import complete, load_prompt

logger = logging.getLogger(__name__)

# Blocklist — comments containing these words are flagged (configurable via env)
COMMENT_BLOCKLIST = os.getenv("COMMENT_BLOCKLIST", "great post,thanks for sharing,very informative").split(",")
MAX_COMMENT_LENGTH = int(os.getenv("MAX_COMMENT_LENGTH", "280"))


def generate_comments(
    post_text: str,
    author_headline: str,
    niche: str,
    model: str | None = None,
    n_variants: int = 3,
) -> list[dict]:
    """
    Generate comment variants for a given post.

    Returns list of dicts: [{"text": "...", "flagged": bool, "rank": int}, ...]
    """
    system_prompt = load_prompt("comment_system").format(niche=niche)
    user_prompt = load_prompt("comment_user").format(
        post_text=post_text[:500],
        author_headline=author_headline,
        n_variants=n_variants,
    )

    raw = complete(
        prompt=user_prompt,
        system=system_prompt,
        model=model,
        max_tokens=500,
        temperature=0.7,
    )

    # Parse response — one comment per line
    lines = [line.strip() for line in raw.split("\n") if line.strip()]
    variants = []
    for i, line in enumerate(lines[:n_variants]):
        # Strip leading numbering (e.g. "1. " or "1) ")
        text = re.sub(r"^\d+[\.\)]\s*", "", line)

        # Truncate if too long
        if len(text) > MAX_COMMENT_LENGTH:
            text = text[:MAX_COMMENT_LENGTH].rsplit(" ", 1)[0] + "..."

        flagged = any(bl in text.lower() for bl in COMMENT_BLOCKLIST if bl)

        variants.append({
            "text": text,
            "flagged": flagged,
            "rank": i + 1,
        })

    logger.info("Generated %d comment variants (%d flagged)", len(variants), sum(1 for v in variants if v["flagged"]))
    return variants