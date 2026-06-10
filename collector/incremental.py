"""Incremental collection — skip already-seen posts/profiles."""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def get_unseen_keywords(keywords: list[str], since_days: int = 7) -> list[str]:
    """
    Return keywords not yet searched in the last N days.
    Phase 1: returns all keywords (no DB check yet for simplicity).
    Phase 2+: query the actions/posts tables for existing data.
    """
    # Phase 1 stub — always returns all keywords
    logger.info("Phase 1: returning all %d keywords (no filtering)", len(keywords))
    return keywords