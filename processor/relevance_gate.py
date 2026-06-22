"""
LLM relevance gate — the one thing heuristics can't do.

The semantic filter and regex noise filters match *surface form*. They cannot
judge author/topic ICP fit, intent, or whether a post is genuinely worth a
relationship-building comment. This module runs a single batched LLM pass over
the filtered survivors and returns a structured keep/score per post, reusing
the niche/ICP context (``build_niche_prompt_context``) that nothing else uses.

Usage:
    from processor.relevance_gate import score_relevance

    gated = score_relevance(filtered_posts, config)   # aligned with input order
    keepers = [p for p, g in zip(filtered_posts, gated) if g["keep"]]
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Fail-open default applied when the LLM output can't be parsed for a post — we
# would rather keep a post and let the heuristic ranker handle it than silently
# drop something good because of a parsing hiccup.
_FALLBACK = {
    "icp_fit": 0,
    "commentability": 0,
    "value_opportunity": 0,
    "composite": 0.0,
    "keep": True,
    "reason": "ungated (parse fallback)",
}


def _parse_json_array(raw: str) -> list[dict]:
    """Extract a JSON array from an LLM response, tolerating fences/preamble."""
    if not raw:
        return []
    s = raw.strip()
    # Strip code fences if present
    if s.startswith("```"):
        s = s.split("```", 2)[1] if s.count("```") >= 2 else s
        s = s.lstrip("json").lstrip()
    # Slice from first '[' to last ']'
    start = s.find("[")
    end = s.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        data = json.loads(s[start : end + 1])
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _build_posts_block(batch: list[dict], max_chars: int = 400) -> str:
    """Render a batch of posts as a numbered block (1-indexed within the batch)."""
    lines = []
    for j, p in enumerate(batch, 1):
        author = (p.get("author_headline") or p.get("author_name") or "unknown").strip()
        text = (p.get("text") or "").replace("\n", " ").strip()[:max_chars]
        lines.append(f"[{j}] Author: {author}\n{text}")
    return "\n\n".join(lines)


def score_relevance(
    posts: list[dict],
    config,
    batch_size: int = 15,
    model: Optional[str] = None,
) -> list[dict]:
    """
    Run the relevance gate over ``posts`` and return a list aligned with the
    input order. Each element is a dict with: ``icp_fit``, ``commentability``,
    ``value_opportunity`` (1-5), ``composite`` (0-1), ``keep`` (bool),
    ``reason`` (str).

    One LLM call per ``batch_size`` posts. Deterministic (temperature 0).
    """
    from content.llm_client import complete, load_prompt
    from config_loader import build_niche_prompt_context

    if not posts:
        return []

    # Inject ICP context. Use replace (not str.format): both the niche text and
    # the JSON spec in the template contain literal braces that .format() chokes on.
    niche_ctx = build_niche_prompt_context(config.client.niche)
    system_prompt = load_prompt("relevance_gate_system").replace(
        "{niche_prompt_context}", niche_ctx
    )
    user_template = load_prompt("relevance_gate_user")

    effective_model = model or getattr(config.llm, "scoring_model", None)

    results: list[dict] = [dict(_FALLBACK) for _ in posts]

    for start in range(0, len(posts), batch_size):
        batch = posts[start : start + batch_size]
        posts_block = _build_posts_block(batch)
        user_prompt = user_template.replace("{posts_block}", posts_block)

        try:
            raw = complete(
                prompt=user_prompt,
                system=system_prompt,
                model=effective_model,
                max_tokens=1200,
                temperature=0.0,
                config=config,
            )
        except Exception as e:  # noqa: BLE001 — never abort the pipeline on a gate failure
            logger.warning("Relevance gate batch %d failed (%s); keeping batch ungated", start, e)
            continue

        parsed = _parse_json_array(raw)
        by_index = {}
        for obj in parsed:
            if isinstance(obj, dict) and "i" in obj:
                try:
                    by_index[int(obj["i"])] = obj
                except (ValueError, TypeError):
                    continue

        for j, _ in enumerate(batch, 1):
            obj = by_index.get(j)
            global_idx = start + (j - 1)
            if not obj:
                continue  # leave fail-open fallback
            icp = int(obj.get("icp_fit", 0) or 0)
            com = int(obj.get("commentability", 0) or 0)
            val = int(obj.get("value_opportunity", 0) or 0)
            results[global_idx] = {
                "icp_fit": icp,
                "commentability": com,
                "value_opportunity": val,
                "composite": round((icp + com + val) / 15.0, 4),
                "keep": bool(obj.get("keep", False)),
                "reason": str(obj.get("reason", ""))[:80],
            }

    kept = sum(1 for r in results if r["keep"])
    logger.info("Relevance gate: %d kept / %d dropped (of %d)", kept, len(results) - kept, len(results))
    return results
