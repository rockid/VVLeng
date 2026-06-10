"""Map raw Apify actor output to internal Python objects."""

import logging
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)


def normalise_posts(raw: list[dict]) -> list[dict]:
    """
    Map Apify post-search output to internal Post dicts (JSON-safe).
    Expected fields vary by actor — this is the translation layer.

    Returns list of dicts matching the Post model schema.
    """
    posts = []
    for item in raw:
        try:
            post = {
                "id": str(uuid4()),
                "url": item.get("postUrl") or item.get("url") or "",
                "text": item.get("text") or item.get("caption") or "",
                "likes_count": _safe_int(item, "likesCount", "stats.likes", "likes"),
                "comments_count": _safe_int(item, "commentsCount", "stats.comments", "comments"),
                "posted_at": item.get("postedAt") or item.get("date") or None,
                "author_name": item.get("authorName") or item.get("author", {}).get("name") or "",
                "author_headline": item.get("authorHeadline") or "",
                "author_url": item.get("authorUrl") or item.get("author", {}).get("url") or "",
            }
            posts.append(post)
        except Exception as e:
            logger.warning("Skipping malformed post item: %s", e)
    return posts


def normalise_profiles(raw: list[dict]) -> list[dict]:
    """
    Map Apify profile-scraper output to internal Profile dicts.
    """
    profiles = []
    for item in raw:
        try:
            profile = {
                "id": str(uuid4()),
                "linkedin_urn": item.get("profileId") or item.get("urn") or item.get("publicIdentifier") or None,
                "full_name": item.get("fullName") or item.get("name") or "",
                "headline": item.get("headline") or item.get("about") or "",
                "follower_count": _safe_int(item, "followersCount", "followers", "stats.followers"),
                "connection_count": _safe_int(item, "connectionsCount", "connections", "stats.connections"),
                "last_activity_date": item.get("lastActivityDate") or item.get("lastPostDate") or None,
            }
            profiles.append(profile)
        except Exception as e:
            logger.warning("Skipping malformed profile item: %s", e)
    return profiles


def _safe_int(item: dict, *keys: str, default: int = 0) -> int:
    """Try multiple key paths to extract an integer value."""
    for key in keys:
        if "." in key:
            parts = key.split(".")
            val = item
            for part in parts:
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                    break
            if val is not None:
                return int(val)
        else:
            val = item.get(key)
            if val is not None:
                return int(val)
    return default