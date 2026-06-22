"""Comment generation — LLM-powered with guardrails."""

import os
import re
import json
import logging
from typing import Any, Optional

from .llm_client import complete, load_prompt

logger = logging.getLogger(__name__)

# Blocklist — comments containing these words are flagged (configurable via env)
COMMENT_BLOCKLIST = os.getenv(
    "COMMENT_BLOCKLIST",
    "great post,thanks for sharing,very informative,well said,spot on,couldn't agree more,love this",
).split(",")
# Structured (hook/value/closer) comments run longer than a one-liner; keep a
# generous ceiling so we don't truncate mid-thought.
MAX_COMMENT_LENGTH = int(os.getenv("MAX_COMMENT_LENGTH", "700"))


def rank_comment_variants(
    post_text: str,
    author_headline: str,
    variants: list[dict],
    niche: str,
    model: str | None = None,
    config: Optional[object] = None,
) -> list[dict]:
    """
    Use an LLM judge to order comment variants best-first and annotate the top
    pick with ``recommended``, ``pick_rank``, ``confidence`` (1-5),
    ``top_reason``, and ``safe_to_autopost``.

    Returns the variants reordered (best first). On any failure the original
    order is returned unchanged so the pipeline never breaks on ranking.
    """
    if len(variants) <= 1:
        for r, v in enumerate(variants, 1):
            v["pick_rank"] = r
            v["recommended"] = (r == 1)
        return variants

    system_prompt = load_prompt("comment_rank_system").replace("{niche}", niche or "")
    block = "\n".join(f"[{i + 1}] {v['text']}" for i, v in enumerate(variants))
    user_prompt = (
        load_prompt("comment_rank_user")
        .replace("{author_headline}", author_headline or "")
        .replace("{post_text}", (post_text or "")[:600])
        .replace("{variants_block}", block)
    )

    effective_model = model
    if effective_model is None and config and hasattr(config, "llm"):
        effective_model = getattr(config.llm, "scoring_model", None)

    try:
        raw = complete(prompt=user_prompt, system=system_prompt, model=effective_model,
                       max_tokens=200, temperature=0.0, config=config)
        obj = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        order = [int(x) for x in (obj.get("order") or [])]
        confidence = int(obj.get("confidence", 0) or 0)
        reason = str(obj.get("reason", ""))[:80]
        safe = bool(obj.get("safe", True))
    except Exception as e:  # noqa: BLE001 — ranking is best-effort
        logger.warning("Comment ranking failed (%s); keeping generation order", e)
        for r, v in enumerate(variants, 1):
            v["pick_rank"] = r
            v["recommended"] = (r == 1)
        return variants

    ordered, seen = [], set()
    for idx in order:
        k = idx - 1
        if 0 <= k < len(variants) and k not in seen:
            ordered.append(variants[k])
            seen.add(k)
    for k, v in enumerate(variants):
        if k not in seen:
            ordered.append(v)

    for r, v in enumerate(ordered, 1):
        v["pick_rank"] = r
        v["recommended"] = (r == 1)
    ordered[0]["confidence"] = confidence
    ordered[0]["top_reason"] = reason
    ordered[0]["safe_to_autopost"] = safe
    logger.info("Ranked %d variants — top confidence=%d safe=%s", len(ordered), confidence, safe)
    return ordered


def generate_comments(
    post_text: str,
    author_headline: str,
    niche: str,
    model: str | None = None,
    n_variants: int = 3,
    config: Optional[object] = None,
    rank: bool = True,
) -> list[dict]:
    """
    Generate comment variants for a given post.

    Returns list of dicts: [{"text": "...", "flagged": bool, "rank": int, ...}].
    When ``rank`` is True, an LLM judge reorders them best-first and annotates the
    top pick (``recommended``, ``confidence``, ``top_reason``, ``safe_to_autopost``).
    """
    system_prompt = load_prompt("comment_system").format(niche=niche)
    user_prompt = load_prompt("comment_user").format(
        post_text=post_text[:500],
        author_headline=author_headline,
        n_variants=n_variants,
    )

    # Determine model: explicit arg → config → default
    effective_model = model
    if effective_model is None:
        if config and hasattr(config, "llm") and hasattr(config.llm, "comment_model"):
            effective_model = config.llm.comment_model

    raw = complete(
        prompt=user_prompt,
        system=system_prompt,
        model=effective_model,
        max_tokens=500,
        temperature=0.7,
        config=config,
    )

    # Parse response — variants are separated by a line containing only ===.
    # Each variant may itself span multiple lines (hook / value / closer), so we
    # must NOT split on every newline. Fall back to blank-line, then single-line
    # splitting if the model ignored the delimiter.
    if re.search(r"(?m)^\s*={3,}\s*$", raw):
        parts = re.split(r"(?m)^\s*={3,}\s*$", raw)
    elif "\n\n" in raw:
        parts = raw.split("\n\n")
    else:
        parts = raw.split("\n")

    variants = []
    for i, part in enumerate([p for p in (s.strip() for s in parts) if p][:n_variants]):
        # Strip leading numbering/bullets (e.g. "1. ", "1) ", "- ", "• ")
        text = re.sub(r"^\s*(?:\d+[\.\)]|[-•*])\s*", "", part).strip()
        # Strip surrounding quotes the model sometimes adds
        text = text.strip('"').strip()

        # Truncate if too long (rare at 700 chars)
        if len(text) > MAX_COMMENT_LENGTH:
            text = text[:MAX_COMMENT_LENGTH].rsplit(" ", 1)[0] + "..."

        flagged = any(bl.strip() in text.lower() for bl in COMMENT_BLOCKLIST if bl.strip())

        variants.append({
            "text": text,
            "flagged": flagged,
            "rank": i + 1,
        })

    logger.info("Generated %d comment variants (%d flagged)", len(variants), sum(1 for v in variants if v["flagged"]))

    if rank and len(variants) > 1:
        variants = rank_comment_variants(post_text, author_headline, variants, niche,
                                         model=model, config=config)
    return variants