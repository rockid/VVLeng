"""
Heuristic post scoring — ranks posts for commenting and repost value.

Replaces "send everything to LLM" with a ranked decision.
All dimensions are computed from the post dict alone — no API calls.

Usage:
    from processor.post_scorer import score_post, PostScore

    scored = [score_post(p, config) for p in posts]          # all posts
    scored.sort(key=lambda x: x.score, reverse=True)         # rank
    top = [s for s in scored if s.post_type == "comment_target"][:limit]
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Heuristic pattern for celebratory / non-actionable posts ──────────────
_CELEBRATORY_PATTERNS = re.compile(
    r"\b("
    r"hiring|new role|new chapter|thrilled to announce|excited to announce"
    r"|excited to share|pleased to announce|happy to share that I"
    r"|I am thrilled|I'm thrilled|joining the team|joined the team"
    r"|promoted to|work anniversary|celebrating|grateful for"
    r"|congratulations|internship|scholarship|graduated|graduation"
    r"|open to work|open to opportunities"
    r")\b",
    re.IGNORECASE,
)


@dataclass
class PostScore:
    """Scoring result for a single post.

    Attributes
    ----------
    score : float
        Composite score 0.0–1.0 (higher = better comment target).
    freshness : float
        Normalised freshness sub-score (0.0–1.0).
    velocity : float
        Engagement velocity sub-score (0.0–1.0), capped.
    relevance : float
        Keyword-tier weight (1.0, 0.7, 0.85).
    opportunity : float
        Comment opportunity sub-score (0.0–1.0).
    post_type : str
        One of ``"comment_target"``, ``"repost_candidate"``, ``"avoid"``.
    avoid_reason : str
        Populated if ``post_type == "avoid"``.
    """

    score: float = 0.0
    freshness: float = 0.0
    velocity: float = 0.0
    relevance: float = 0.0
    opportunity: float = 0.0
    post_type: str = "comment_target"
    avoid_reason: str = ""


def _compute_freshness(posted_at_str: str | None) -> float:
    """
    Normalised freshness sub-score.

    - < 6h   → 1.0
    - < 12h  → 0.8
    - < 24h  → 0.5
    - < 48h  → 0.2
    - older  → 0.0
    """
    if not posted_at_str:
        return 0.0
    try:
        dt = datetime.fromisoformat(posted_at_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.0

    age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    if age_hours < 0:
        return 0.0  # future date — shouldn't happen
    if age_hours < 6:
        return 1.0
    if age_hours < 12:
        return 0.8
    if age_hours < 24:
        return 0.5
    if age_hours < 48:
        return 0.2
    return 0.0


def _compute_velocity(post: dict) -> float:
    """
    Normalised engagement velocity sub-score.

    ``(likes + comments) / max(hours_since_posted, 1)``, then
    soft-capped at 10 → normalised to [0.0, 1.0].
    """
    likes = post.get("likes_count", 0) or 0
    comments = post.get("comments_count", 0) or 0
    total_eng = likes + comments

    posted_at = post.get("posted_at")
    if not posted_at:
        return 0.0

    try:
        dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_hours = max((datetime.now(timezone.utc) - dt).total_seconds() / 3600, 1.0)
    except (ValueError, TypeError):
        return 0.0

    raw_velocity = total_eng / age_hours
    # Soft-cap at 10 → normalise to [0, 1]
    return min(raw_velocity / 10.0, 1.0)


def _compute_opportunity(post: dict) -> float:
    """
    Comment opportunity sub-score — how likely a comment will be seen.

    - 5–30  comments → 1.0   (sweet spot)
    - 0     comments → 0.5   (post may be too new / low interest)
    - 1–4   comments → 0.7   (small — likely still visible)
    - 31–100        → 0.3   (buried but might be seen)
    - >100  comments → 0.0   (too noisy)
    """
    comments = post.get("comments_count", 0) or 0
    if comments > 100:
        return 0.0
    if comments > 30:
        return 0.3
    if comments >= 5:
        return 1.0
    if comments > 0:
        return 0.7  # 1–4
    return 0.5  # 0 comments


def _compute_relevance(post: dict) -> float:
    """
    Topic relevance based on keyword tier.

    - tier1  → 1.0   (direct practitioner vocabulary)
    - tier2  → 0.7   (adjacent — broader, more noise)
    - tier3  → 0.85  (platform names — product-aware practitioners)
    - unknown → 0.4
    """
    tier = (post.get("keyword_tier") or "tier1").lower()
    return {"tier1": 1.0, "tier2": 0.7, "tier3": 0.85}.get(tier, 0.4)


def _is_competitor_post(post: dict, config) -> bool:
    """
    Check if the author matches a known competitor domain.

    Simple heuristic: if the author's headline or URL contains any
    competitor-domain keyword.  (Extend config with a
    ``competitor_domains`` list when needed — currently empty.)
    """
    # Placeholder: expand if config.client.filter.competitor_domains added
    return False


def _is_celebratory(text: str) -> bool:
    """Return True if the post text matches celebratory/non-actionable patterns."""
    return bool(_CELEBRATORY_PATTERNS.search(text))


def score_post(post: dict, config) -> PostScore:
    """
    Compute a composite score and post-type classification for one post.

    Parameters
    ----------
    post : dict
        Normalised post dict.
    config : AppConfig
        Application config (reads scoring thresholds, action limits, etc.).

    Returns
    -------
    PostScore
    """
    text = (post.get("text") or "").strip()
    if not text:
        return PostScore(post_type="avoid", avoid_reason="empty text")

    # ── Check avoid conditions (fast-path) ──────────────────────────
    comments = post.get("comments_count", 0) or 0
    if comments > 100:
        return PostScore(post_type="avoid", avoid_reason=">100 comments")

    if _is_celebratory(text):
        return PostScore(post_type="avoid", avoid_reason="celebratory / non-actionable")

    if _is_competitor_post(post, config):
        return PostScore(post_type="avoid", avoid_reason="competitor author")

    # ── Compute sub-scores ──────────────────────────────────────────
    freshness = _compute_freshness(post.get("posted_at"))
    velocity = _compute_velocity(post)
    relevance = _compute_relevance(post)
    opportunity = _compute_opportunity(post)

    # Composite with configurable weights
    composite = (
        freshness * 0.35 + velocity * 0.25 + relevance * 0.25 + opportunity * 0.15
    )

    # ── Post type classification ────────────────────────────────────
    # Repost candidate: high-authority post that's past best commenting window
    posted_at = post.get("posted_at")
    is_past_comment_window = False
    if posted_at:
        try:
            dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            is_past_comment_window = age_hours >= 12
        except (ValueError, TypeError):
            pass

    # A repost candidate has high relevance + past commenting window
    # + from an influential profile (follower_count > threshold)
    follower_threshold = getattr(config.client.scoring, "influencer_follower_threshold", 5000)
    author_followers = post.get("author_followers", 0) or 0

    if is_past_comment_window and relevance >= 0.85 and author_followers >= follower_threshold:
        post_type = "repost_candidate"
    elif composite > 0.0:
        post_type = "comment_target"
    else:
        post_type = "avoid"
        avoid_reason = "zero composite score"

    return PostScore(
        score=round(composite, 4),
        freshness=round(freshness, 4),
        velocity=round(velocity, 4),
        relevance=round(relevance, 4),
        opportunity=round(opportunity, 4),
        post_type=post_type,
        avoid_reason=avoid_reason if post_type == "avoid" else "",
    )