"""Profile deduplication — merge profiles by URN or name+company."""

import logging

logger = logging.getLogger(__name__)


def dedup_profiles(profiles: list[dict]) -> list[dict]:
    """
    Merge profiles by linkedin_urn. If URN absent, match on full_name.

    Phase 1: simple dedup by URN only. Phase 2+ will add company matching.
    """
    seen_by_urn: dict[str, dict] = {}
    seen_by_name: dict[str, dict] = {}
    merged: list[dict] = []
    duplicates_removed = 0

    for profile in profiles:
        urn = profile.get("linkedin_urn")
        name = (profile.get("full_name") or "").strip()

        if urn:
            if urn in seen_by_urn:
                # Merge engagement data (pick higher follower count)
                existing = seen_by_urn[urn]
                if (profile.get("follower_count") or 0) > (existing.get("follower_count") or 0):
                    existing["follower_count"] = profile["follower_count"]
                duplicates_removed += 1
            else:
                seen_by_urn[urn] = profile
                merged.append(profile)
        elif name:
            if name in seen_by_name:
                duplicates_removed += 1
            else:
                seen_by_name[name] = profile
                merged.append(profile)
        else:
            # No URN and no name — still include but log warning
            logger.warning("Profile with no URN or name found")
            merged.append(profile)

    logger.info("Dedup: %d input → %d output (%d duplicates removed)",
                len(profiles), len(merged), duplicates_removed)
    return merged