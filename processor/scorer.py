"""Lead scoring — relevance, influence, recency, engagement."""

import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Scoring thresholds from .env
TIER_A_THRESHOLD = float(os.getenv("SCORING_TIER_A_THRESHOLD", "0.65"))
TIER_B_THRESHOLD = float(os.getenv("SCORING_TIER_B_THRESHOLD", "0.40"))


def score_profiles(profiles: list[dict], niche_keywords: list[str]) -> list[dict]:
    """
    Score each profile and assign a tier (A/B/C).

    Scoring formula (v1):
        relevance   = tfidf_similarity(headline + about, niche_keywords)  — approximated via keyword match ratio
        influence   = min(follower_count / 10000, 1.0)
        recency     = 1.0 if last_activity < 14d else 0.5 if < 30d else 0.1
        engagement  = min(comment_word_count / 20, 1.0)  — approximated as constant 0.5 for Phase 1

        overall = (relevance * 0.4) + (influence * 0.25) + (recency * 0.2) + (engagement * 0.15)
    """
    scored = []
    for profile in profiles:
        try:
            headline = profile.get("headline", "") or ""
            full_name = profile.get("full_name", "") or ""

            # Relevance: simple keyword match ratio (Phase 1 approximation of TF-IDF)
            text_blob = (headline + " " + full_name).lower()
            if niche_keywords and text_blob:
                matches = sum(1 for kw in niche_keywords if kw.lower() in text_blob)
                relevance = min(matches / max(len(niche_keywords), 1), 1.0)
            else:
                relevance = 0.0

            # Influence: follower count, capped at 10k
            follower_count = profile.get("follower_count", 0) or 0
            influence = min(follower_count / 10000.0, 1.0)

            # Recency: Phase 1 default — assume moderate recency
            recency = 0.5

            # Engagement: Phase 1 default
            engagement = 0.5

            # Overall score
            overall = (relevance * 0.4) + (influence * 0.25) + (recency * 0.2) + (engagement * 0.15)

            # Tier assignment
            if overall >= TIER_A_THRESHOLD:
                tier = "A"
            elif overall >= TIER_B_THRESHOLD:
                tier = "B"
            else:
                tier = "C"

            profile["relevance_score"] = round(relevance, 4)
            profile["influence_score"] = round(influence, 4)
            profile["overall_score"] = round(overall, 4)
            profile["tier"] = tier

            scored.append(profile)
        except Exception as e:
            logger.warning("Error scoring profile %s: %s", profile.get("full_name", "unknown"), e)
            profile["relevance_score"] = 0.0
            profile["influence_score"] = 0.0
            profile["overall_score"] = 0.0
            profile["tier"] = "C"
            scored.append(profile)

    logger.info("Scored %d profiles — A: %d, B: %d, C: %d",
                len(scored),
                sum(1 for p in scored if p["tier"] == "A"),
                sum(1 for p in scored if p["tier"] == "B"),
                sum(1 for p in scored if p["tier"] == "C"))
    return scored