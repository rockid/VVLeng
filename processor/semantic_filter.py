"""
Semantic pre-filter using sentence-transformers.

Reduces post volume ~70‑80% before any LLM calls.
Zero API cost. Runs on CPU.

Usage:
    from processor.semantic_filter import build_niche_embedding, passes_filter

    niche_emb = build_niche_embedding(niche_embedding_text)
    posts = [p for p in all_posts if passes_filter(p, niche_emb, config)]
"""

import logging
from functools import lru_cache

import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"  # 80 MB download, cached after first use


@lru_cache(maxsize=1)
def get_model():
    """Lazy-load the sentence-transformer model (cached for lifetime of process)."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def build_niche_embedding(niche_text: str) -> np.ndarray:
    """
    Compute the niche embedding once at pipeline startup.

    Parameters
    ----------
    niche_text : str
        Dense concatenated text from ``build_niche_embedding_text()``.

    Returns
    -------
    np.ndarray
        Embedding vector (384-dim for all-MiniLM-L6-v2).
    """
    model = get_model()
    emb = model.encode(niche_text, convert_to_tensor=False)
    logger.info(
        "Niche embedding computed (text length=%d chars, shape=%s)",
        len(niche_text),
        emb.shape,
    )
    return emb


def passes_filter(
    post: dict,
    niche_embedding: np.ndarray,
    config,
) -> tuple[bool, float]:
    """
    Apply semantic similarity gate to a single post dict.

    The cheap checks (blocked substrings, min length) are applied first so we
    don't waste embedding computation on obviously irrelevant posts.

    Parameters
    ----------
    post : dict
        Normalised post dict (must have ``text`` key).
    niche_embedding : np.ndarray
        Pre-computed niche embedding vector.
    config : AppConfig
        Application config (read ``config.client.filter.*``).

    Returns
    -------
    (passed, score)
        ``passed`` is True if the post survives the filter gate.
        ``score`` is the raw cosine similarity (0‑1 range).
    """
    text = (post.get("text") or "").strip()
    if not text:
        return False, 0.0

    # ── Cheap pre-checks (no embedding needed) ──────────────────────
    client = config.client

    # Blocked substrings
    blocked = list(client.filter.blocked_substrings)
    text_lower = text.lower()
    for bs in blocked:
        if bs.lower() in text_lower:
            return False, 0.0

    # Min text length
    min_len = config.defaults.min_post_length_chars
    if len(text) < min_len:
        return False, 0.0

    # ── Semantic scoring ────────────────────────────────────────────
    model = get_model()
    post_embedding = model.encode(text, convert_to_tensor=False)
    # Cosine similarity
    score = float(
        np.dot(niche_embedding, post_embedding)
        / (np.linalg.norm(niche_embedding) * np.linalg.norm(post_embedding) + 1e-10)
    )

    # Tier multiplier
    keyword_tier = post.get("keyword_tier", "tier1") or "tier1"
    multiplier = {"tier1": 1.0, "tier2": 1.2, "tier3": 0.85}.get(keyword_tier, 1.0)

    threshold = client.filter.min_semantic_similarity * multiplier
    passed = score >= threshold

    logger.debug(
        "Semantic filter: score=%.4f  threshold=%.4f  tier=%s  passed=%s  preview=%.60s",
        score,
        threshold,
        keyword_tier,
        passed,
        text,
    )
    return passed, score


_TIER_MULTIPLIER = {"tier1": 1.0, "tier2": 1.2, "tier3": 0.85}


def evaluate_posts(
    posts: list[dict],
    niche_embedding: np.ndarray,
    config,
) -> list[tuple[dict, bool, float]]:
    """
    Batched semantic evaluation for a list of posts.

    Equivalent to calling :func:`passes_filter` on each post, but encodes all
    surviving posts in a single ``model.encode`` batch — roughly an order of
    magnitude faster than encoding one post at a time on CPU.

    Cheap pre-checks (blocked substrings, min length) are applied first so we
    never embed an obviously irrelevant post.

    Returns a list of ``(post, passed, score)`` tuples in the original order.
    Posts rejected by a cheap pre-check get ``score == 0.0``.
    """
    client = config.client
    blocked = [bs.lower() for bs in client.filter.blocked_substrings]
    min_len = config.defaults.min_post_length_chars
    base_threshold = client.filter.min_semantic_similarity

    results: list[tuple[dict, bool, float] | None] = [None] * len(posts)
    to_encode: list[str] = []
    encode_idx: list[int] = []

    for i, p in enumerate(posts):
        text = (p.get("text") or "").strip()
        if not text:
            results[i] = (p, False, 0.0)
            continue
        tl = text.lower()
        if any(bs in tl for bs in blocked):
            results[i] = (p, False, 0.0)
            continue
        if len(text) < min_len:
            results[i] = (p, False, 0.0)
            continue
        to_encode.append(text)
        encode_idx.append(i)

    if to_encode:
        model = get_model()
        embs = model.encode(
            to_encode, convert_to_tensor=False, batch_size=64, show_progress_bar=False
        )
        niche_norm = float(np.linalg.norm(niche_embedding)) + 1e-10
        for j, i in enumerate(encode_idx):
            e = embs[j]
            score = float(np.dot(niche_embedding, e) / (niche_norm * np.linalg.norm(e) + 1e-10))
            p = posts[i]
            tier = (p.get("keyword_tier") or "tier1")
            multiplier = _TIER_MULTIPLIER.get(tier, 1.0)
            threshold = base_threshold * multiplier
            results[i] = (p, score >= threshold, score)

    return [r for r in results if r is not None]