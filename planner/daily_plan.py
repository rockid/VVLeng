"""Daily plan builder — prioritise actions and enforce limits."""

import os
import logging
from datetime import datetime, date
from typing import Any, Optional

logger = logging.getLogger(__name__)


def build_daily_plan(
    posts: list[dict],
    profiles: list[dict],
    comments_map: dict[str, list[dict]],  # post_id → comment variants
    existing_actions: list[dict] | None = None,
    config: Optional[object] = None,
    run_date: Optional[str] = None,
) -> dict:
    """
    Build a daily action plan.

    Priority order:
    1. Posts under 12 hours old (visibility window still open)
    2. Tier A profiles not yet contacted
    3. Follow-up on previous comments that received a reply
    4. Tier B profiles (warm-up actions)

    Limits are read from config (config.client.action_limits), then env vars,
    then hardcoded defaults.

    ``run_date`` dates the plan (and, downstream, the daily_log/run_costs sheet
    rows). Defaults to today — pass the actual collection date explicitly when
    reprocessing already-collected data (``--skip-collect``), so a rerun that
    crosses midnight doesn't fork onto a new date and break the daily_log
    per-action_id dedup guard, which keys on (date, action_id).

    Returns a plan dict matching the schema in §9 of the architecture spec.
    """
    plan_date = run_date or date.today().isoformat()

    # Read action limits from config → env → defaults
    if config and hasattr(config, "client") and hasattr(config.client, "action_limits"):
        al = config.client.action_limits
        limit_connections = getattr(al, "connections_per_day", 15)
        limit_comments = getattr(al, "comments_per_day", 8)
        limit_visits = getattr(al, "visits_per_day", 25)
    else:
        limit_connections = int(os.getenv("LIMIT_CONNECTIONS_PER_DAY", "15"))
        limit_comments = int(os.getenv("LIMIT_COMMENTS_PER_DAY", "8"))
        limit_visits = int(os.getenv("LIMIT_VISITS_PER_DAY", "25"))

    # Niche description from config
    niche_desc = ""
    if config and hasattr(config, "client") and hasattr(config.client, "niche_description"):
        niche_desc = config.client.niche_description
    if not niche_desc:
        niche_desc = os.getenv("NICHE_DESCRIPTION", "")

    actions: list[dict] = []
    comments_used = 0
    connections_used = 0
    visits_used = 0

    # 1. Recent posts → comment actions
    if limit_comments > 0:
        for post in posts:
            if comments_used >= limit_comments:
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
    if limit_connections > 0:
        for profile in profiles:
            if connections_used >= limit_connections:
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
    if limit_visits > 0:
        for profile in profiles:
            if visits_used >= limit_visits:
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
        "niche": niche_desc or "Not configured",
        "capacity": {
            "connections_remaining": limit_connections - connections_used,
            "comments_remaining": limit_comments - comments_used,
            "visits_remaining": limit_visits - visits_used,
        },
        "actions": actions,
        "content_ideas": [],
        "follow_ups": [],
    }

    logger.info("Daily plan built: %d actions (%d comments, %d connections, %d visits)",
                len(actions), comments_used, connections_used, visits_used)
    return plan