"""Daily plan builder — prioritise actions and enforce limits."""

import os
import logging
from datetime import datetime, date
from typing import Any

logger = logging.getLogger(__name__)

# Daily limits from .env
LIMIT_CONNECTIONS = int(os.getenv("LIMIT_CONNECTIONS_PER_DAY", "15"))
LIMIT_COMMENTS = int(os.getenv("LIMIT_COMMENTS_PER_DAY", "8"))
LIMIT_VISITS = int(os.getenv("LIMIT_VISITS_PER_DAY", "25"))


def build_daily_plan(
    posts: list[dict],
    profiles: list[dict],
    comments_map: dict[str, list[dict]],  # post_id → comment variants
    existing_actions: list[dict] | None = None,
) -> dict:
    """
    Build a daily action plan.

    Priority order:
    1. Posts under 12 hours old (visibility window still open)
    2. Tier A profiles not yet contacted
    3. Follow-up on previous comments that received a reply
    4. Tier B profiles (warm-up actions)

    Returns a plan dict matching the schema in §9 of the architecture spec.
    """
    plan_date = date.today().isoformat()
    niche = os.getenv("NICHE_DESCRIPTION", "")

    actions: list[dict] = []
    comments_used = 0
    connections_used = 0
    visits_used = 0

    # 1. Recent posts → comment actions
    if LIMIT_COMMENTS > 0:
        for post in posts:
            if comments_used >= LIMIT_COMMENTS:
                break
            post_id = post.get("id", "")
            post_url = post.get("url", "")
            posted_at = post.get("posted_at")
            is_recent = False
            if posted_at:
                try:
                    posted_dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
                    age_hours = (datetime.utcnow() - posted_dt).total_seconds() / 3600
                    is_recent = age_hours < 12
                except (ValueError, TypeError):
                    pass

            variants = comments_map.get(post_id, [])
            if not variants:
                continue

            actions.append({
                "action_id": f"act_{len(actions) + 1:03d}",
                "type": "comment",
                "priority": 1 if is_recent else 2,
                "url": post_url,
                "post_preview": post.get("text", "")[:100],
                "author_name": post.get("author_name", ""),
                "author_tier": "A",
                "deadline": "14:00 UTC" if is_recent else "23:00 UTC",
                "suggested_text": [v["text"] for v in variants],
                "status": "suggested",
            })
            comments_used += 1

    # 2. Tier A profiles → connection actions
    if LIMIT_CONNECTIONS > 0:
        for profile in profiles:
            if connections_used >= LIMIT_CONNECTIONS:
                break
            tier = profile.get("tier", "C")
            if tier == "A":
                actions.append({
                    "action_id": f"act_{len(actions) + 1:03d}",
                    "type": "connection",
                    "priority": 2,
                    "url": f"https://www.linkedin.com/in/{profile.get('linkedin_urn', '')}",
                    "person_name": profile.get("full_name", ""),
                    "person_headline": profile.get("headline", ""),
                    "tier": "A",
                    "reason": f"Scored {profile.get('overall_score', 0):.2f} — highly relevant to niche",
                    "suggested_message": [],
                    "status": "suggested",
                })
                connections_used += 1

    # 3. Tier B profiles → visit actions
    if LIMIT_VISITS > 0:
        for profile in profiles:
            if visits_used >= LIMIT_VISITS:
                break
            tier = profile.get("tier", "C")
            if tier == "B":
                actions.append({
                    "action_id": f"act_{len(actions) + 1:03d}",
                    "type": "visit",
                    "priority": 3,
                    "url": f"https://www.linkedin.com/in/{profile.get('linkedin_urn', '')}",
                    "person_name": profile.get("full_name", ""),
                    "person_headline": profile.get("headline", ""),
                    "tier": "B",
                    "reason": "Warm-up — visit profile to increase visibility",
                    "status": "suggested",
                })
                visits_used += 1

    # Build plan
    plan = {
        "date": plan_date,
        "niche": niche or "Not configured",
        "capacity": {
            "connections_remaining": LIMIT_CONNECTIONS - connections_used,
            "comments_remaining": LIMIT_COMMENTS - comments_used,
            "visits_remaining": LIMIT_VISITS - visits_used,
        },
        "actions": actions,
        "content_ideas": [],
        "follow_ups": [],
    }

    logger.info("Daily plan built: %d actions (%d comments, %d connections, %d visits)",
                len(actions), comments_used, connections_used, visits_used)
    return plan