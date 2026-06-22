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

# ── Recruiting / job-post patterns ────────────────────────────────────────
# These dominate the noise in keyword-sourced LinkedIn data: the search
# vocabulary ("community manager", "member engagement") overlaps heavily with
# job ads, which a semantic filter cannot distinguish. Catch them by phrasing.
_RECRUITING_PATTERNS = re.compile(
    r"(?i)("
    r"\bhiring\b|\bnow hiring\b|\bwe(?:'re| are)\s+hiring\b|\bis hiring\b"
    r"|\b(?:looking|searching|on the hunt)\s+for\s+(?:a|an|our|my|some)\b"
    r"|\bseeking\s+(?:a|an|our|experienced|talented|motivated)\b"
    r"|\bjoin\s+(?:my|our|the|a)\s+(?:team|growing team)\b"
    r"|\bjoin\s+a\s+\w+\s+team\b"
    r"|\b(?:open|new)\s+(?:role|roles|position|positions|opening|openings|vacancy|vacancies)\b"
    r"|\b(?:we(?:'re| are))\s+looking\s+for\b"
    r"|\b(?:is|are)\s+(?:expanding|growing)\s+(?:its|our|the|their)\s+team\b"
    r"|\bexpanding\s+(?:its|our|their)\s+\w+\s+team\b"
    r"|\b(?:apply|applications)\s+(?:now|here|today|via|by|before)\b"
    r"|\b(?:send|share|drop)\s+(?:me\s+)?your\s+(?:cv|resume)\b"
    r"|\bthis (?:role|position) (?:is|requires|offers)\b"
    r"|\bto hire (?:a|an|our|their)\b|\bwe(?:'re| are) recruiting\b"
    r"|\bjoin us as\b|\bremote job\b|\bjob (?:portals?|boards?)\b"
    r")"
)

# ── Announcement / personal-milestone patterns ────────────────────────────
_ANNOUNCEMENT_PATTERNS = re.compile(
    r"(?i)("
    r"\b(?:excited|thrilled|delighted|pleased|proud|happy|honou?red)\s+to\s+"
    r"(?:announce|share|welcome|join|be joining|be starting)\b"
    r"|\bwelcome\b.{0,40}\bto the (?:team|family)\b"
    r"|\b(?:i(?:'ve| have)|i(?:'m| am))\s+(?:joined|joining|been appointed|now)\b"
    r"|\bappointed\s+as\b"
    r"|\bnew (?:role|chapter|position|job|adventure|journey)\b"
    r"|\bpromoted to\b|\bwork anniversary\b|\bcelebrating\b|\bgrateful for\b"
    r"|\b\d+(?:st|nd|rd|th)\s+(?:work\s+)?anniversary\b|\banniversary at\b|\bmarks my\b"
    r"|\bcongratulations\b"
    r"|\binternship\b|\bscholarship\b|\bgraduated\b|\bgraduation\b"
    r"|\bopen to (?:work|opportunities)\b"
    r")"
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
    # Final ranking score. Equals ``score`` unless the LLM relevance gate ran,
    # in which case it blends heuristic and gate composite (set in the pipeline).
    rank_score: float = 0.0


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
    Topic relevance — a blend of keyword-tier weight and the actual semantic
    similarity to the niche (when available from the semantic filter).

    Keyword tier alone only says *which bucket* a post matched; the semantic
    score says *how on-topic the text actually is*. Blending both is far more
    discriminating than tier alone and is the main lever for surfacing posts
    genuinely worth commenting on.

    Tier weights:
    - tier1  → 1.0   (direct practitioner vocabulary)
    - tier2  → 0.7   (adjacent — broader, more noise)
    - tier3  → 0.85  (platform names — product-aware practitioners)
    - unknown → 0.4

    The ``semantic_score`` (raw cosine, typically ~0.30–0.60 for relevant posts)
    is normalised onto 0–1 across that operating band. If no semantic score is
    present (e.g. semantic filter skipped), we fall back to tier weight alone.
    """
    tier = (post.get("keyword_tier") or "tier1").lower()
    tier_w = {"tier1": 1.0, "tier2": 0.7, "tier3": 0.85}.get(tier, 0.4)

    sem = post.get("semantic_score")
    if sem is None:
        return tier_w

    # Map cosine 0.30 → 0.0 and 0.55 → 1.0, clamped.
    sem_norm = min(max((float(sem) - 0.30) / 0.25, 0.0), 1.0)
    return round(0.5 * tier_w + 0.5 * sem_norm, 4)


def _is_competitor_post(post: dict, config) -> bool:
    """
    Check if the author matches a known competitor domain.

    Simple heuristic: if the author's headline or URL contains any
    competitor-domain keyword.  (Extend config with a
    ``competitor_domains`` list when needed — currently empty.)
    """
    # Placeholder: expand if config.client.filter.competitor_domains added
    return False


def _noise_reason(text: str) -> str:
    """
    Classify a post as recruiting / announcement noise.

    Returns a short avoid-reason string, or "" if the post is not obviously
    non-actionable. These two classes (job ads and self-announcements) are the
    dominant noise in keyword-sourced LinkedIn data and are never worth a
    relationship-building comment.
    """
    if _RECRUITING_PATTERNS.search(text):
        return "recruiting / job post"
    if _ANNOUNCEMENT_PATTERNS.search(text):
        return "announcement / non-actionable"
    return ""


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

    noise = _noise_reason(text)
    if noise:
        return PostScore(post_type="avoid", avoid_reason=noise)

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

    # Minimum composite a post must clear to be worth a comment. Anything below
    # this is noise — fresh enough to pass the age filter but not a strong
    # engagement opportunity. Configurable per client.
    min_ct = getattr(config.client.scoring, "min_comment_target_score", 0.40)

    avoid_reason = ""
    if is_past_comment_window and relevance >= 0.85 and author_followers >= follower_threshold:
        post_type = "repost_candidate"
    elif composite >= min_ct:
        post_type = "comment_target"
    else:
        post_type = "avoid"
        avoid_reason = f"below comment threshold ({composite:.2f} < {min_ct:.2f})"

    return PostScore(
        score=round(composite, 4),
        freshness=round(freshness, 4),
        velocity=round(velocity, 4),
        relevance=round(relevance, 4),
        opportunity=round(opportunity, 4),
        post_type=post_type,
        avoid_reason=avoid_reason if post_type == "avoid" else "",
        rank_score=round(composite, 4),  # default; pipeline blends in gate when run
    )