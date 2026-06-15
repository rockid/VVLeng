"""Map raw Apify actor output to internal Python objects.

Confirmed field mapping for harvestapi/linkedin-post-search:
  post_id:         item["id"]
  url:             item["linkedinUrl"]
  content:         item["content"]
  author_id:       item["author"]["id"]
  author_name:     item["author"]["name"]
  author_handle:   item["author"]["publicIdentifier"]
  author_url:      item["author"]["linkedinUrl"]
  author_headline: item["author"]["info"]
  posted_at:       item["postedAt"]["date"]
  timestamp_ms:    item["postedAt"]["timestamp"]
  likes:           item["engagement"]["likes"]
  comments:        item["engagement"]["comments"]
  shares:          item["engagement"]["shares"]
  has_images:      len(item.get("postImages", [])) > 0
  source_query:    item["query"]["search"]
"""

import logging
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)


def _get_nested(item: dict, *keys, default=None):
    """Safely traverse nested dict keys. Returns default if any key missing."""
    val = item
    for key in keys:
        if isinstance(val, dict):
            val = val.get(key)
        else:
            return default
    return val if val is not None else default


def _safe_int(item: dict, *keys, default: int = 0) -> int:
    """Try multiple key paths to extract an integer value. Supports dotted nested paths."""
    for key in keys:
        if "." in key:
            val = _get_nested(item, *key.split("."), default=None)
        else:
            val = item.get(key)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                continue
    return default


def normalise_posts(raw: list[dict]) -> list[dict]:
    """
    Map harvestapi/linkedin-post-search output to internal Post dicts (JSON-safe).

    Handles both the harvestapi nested format (primary) and generic flat format (fallback)
    for backward compatibility.
    """
    posts = []
    for item in raw:
        if not isinstance(item, dict):
            logger.warning("Skipping non-dict item")
            continue
        try:
            # Determine format: harvestapi has nested engagement, generic has flat keys
            has_harvestapi = "engagement" in item and isinstance(item["engagement"], dict)

            if has_harvestapi:
                post = _normalise_harvestapi(item)
            else:
                post = _normalise_generic(item)

            posts.append(post)

        except Exception as e:
            logger.warning("Skipping malformed post item: %s", e)

    logger.info("Normalised %d posts from %d raw items", len(posts), len(raw))
    return posts


def _normalise_harvestapi(item: dict) -> dict:
    """Normalise a harvestapi/linkedin-post-search item."""
    author = item.get("author") or {}
    engagement = item.get("engagement") or {}
    posted_at = item.get("postedAt") or {}

    has_images = bool(item.get("postImages"))

    return {
        "id": str(uuid4()),
        "url": item.get("linkedinUrl") or "",
        "text": item.get("content") or "",
        "likes_count": _safe_int(engagement, "likes"),
        "comments_count": _safe_int(engagement, "comments"),
        "posted_at": posted_at.get("date") or None,
        "author_name": author.get("name") or "",
        "author_headline": author.get("info") or "",
        "author_url": author.get("linkedinUrl") or "",
        "author_handle": author.get("publicIdentifier") or "",
        "author_id": author.get("id") or "",
        "shares": _safe_int(engagement, "shares"),
        "has_images": has_images,
        "source_query": _get_nested(item, "query", "search", default=""),
        "linkedin_post_id": item.get("id") or "",
    }


def _normalise_generic(item: dict) -> dict:
    """Normalise a generic/flat format item (backward compat)."""
    return {
        "id": str(uuid4()),
        "url": item.get("postUrl") or item.get("url") or "",
        "text": item.get("text") or item.get("caption") or "",
        "likes_count": _safe_int(item, "likesCount", "likes"),
        "comments_count": _safe_int(item, "commentsCount", "comments"),
        "posted_at": item.get("postedAt") or item.get("date") or None,
        "author_name": item.get("authorName") or _get_nested(item, "author", "name", default=""),
        "author_headline": item.get("authorHeadline") or "",
        "author_url": item.get("authorUrl") or _get_nested(item, "author", "url", default=""),
        "author_handle": item.get("authorHandle") or "",
        "author_id": item.get("authorId") or "",
        "shares": 0,
        "has_images": False,
        "source_query": "",
        "linkedin_post_id": item.get("id") or "",
    }


def normalise_profiles(raw: list[dict]) -> list[dict]:
    """
    Map Apify profile-scraper output to internal Profile dicts.
    """
    profiles = []
    for item in raw:
        if not isinstance(item, dict):
            continue
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