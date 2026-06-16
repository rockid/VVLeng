#!/usr/bin/env python3
"""
Run pipeline using pre-collected scratch files (run-4.json = tier-1, run-5.json = tier-2)
instead of live Apify calls.

Test mode: applies all filters (including semantic) but SKIPS LLM comment generation
so we can inspect which posts survive the full funnel and how they rank.

Usage:
    python scratch/run_tier1_tier2.py

Effect:
    1. Loads scratch/run-4.json (tier-1) and scratch/run-5.json (tier-2)
    2. Normalises → tags each post with its keyword_tier
    3. Applies semantic filter (blocked_substrings + min length + semantic similarity)
    4. Applies age + engagement + dedup filters
    5. Scores + ranks surviving posts via heuristic post_scorer
    6. Prints the full filter funnel + ranked shortlist
    7. Builds a plan WITHOUT real LLM comments — uses placeholder so planner can rank
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, date, timedelta, timezone

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_tier1_tier2")

from config_loader import load_config, ensure_client_dirs, build_niche_embedding_text
from collector.normaliser import normalise_posts
from processor.semantic_filter import build_niche_embedding, passes_filter
from processor.post_scorer import score_post, PostScore
from processor.dedup import dedup_profiles
from processor.scorer import score_profiles
from planner.daily_plan import build_daily_plan
from planner.output import write_plan

# DB imports
from db.session import init_db_from_config, SessionLocal
from db.models import Base, Post, Profile, Action, ContentIdea


def load_scratch_json(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("items", data.get("data", [data]))
    return data


def tag_posts_with_tier(raw_tier1: list[dict], raw_tier2: list[dict]) -> list[dict]:
    """
    Normalise the raw items and tag each post with its keyword_tier.
    Returns a single list of normalised post dicts with a ``keyword_tier`` key.
    """
    tier1_posts = normalise_posts(raw_tier1)
    for p in tier1_posts:
        p["keyword_tier"] = "tier1"

    tier2_posts = normalise_posts(raw_tier2)
    for p in tier2_posts:
        p["keyword_tier"] = "tier2"

    all_posts = tier1_posts + tier2_posts
    logger.info("Tagged %d tier-1 + %d tier-2 = %d posts", len(tier1_posts), len(tier2_posts), len(all_posts))
    return all_posts


def apply_semantic_filter(posts: list[dict], niche_embedding, config) -> tuple[list[dict], dict]:
    """
    Apply the semantic similarity gate + its built-in cheap checks.

    ``passes_filter`` already handles:
      - empty text
      - blocked substrings
      - min text length
      - semantic similarity with tier multiplier

    Returns (kept_posts, dropped_count).
    """
    kept = []
    dropped = 0
    for p in posts:
        passed, score = passes_filter(p, niche_embedding, config)
        if passed:
            p["semantic_score"] = round(score, 4)
            kept.append(p)
        else:
            dropped += 1
    logger.info("Semantic filter: %d kept / %d dropped", len(kept), dropped)
    return kept, dropped


def apply_post_filters(posts: list[dict], config) -> tuple[list[dict], dict]:
    """
    Apply remaining post-level filters NOT covered by the semantic filter.

    Filters applied in order:
      1. Max post age (defaults.max_post_age_days)
      2. Min engagement per tier (client.collection.min_engagement_tier1 / tier2)
      3. Duplicate text detection (simple prefix match)

    Returns (filtered_posts, stats).
    """
    stats = {
        "input_from_semantic": len(posts),
        "removed_too_old": 0,
        "removed_low_engagement": 0,
        "removed_duplicate_text": 0,
        "remaining": 0,
    }

    # --- 1. Max post age ---
    max_age_days = config.defaults.max_post_age_days
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    posts1 = []
    for p in posts:
        posted_at = p.get("posted_at")
        if posted_at:
            try:
                dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt < cutoff:
                    stats["removed_too_old"] += 1
                    continue
            except (ValueError, TypeError):
                pass
        posts1.append(p)
    logger.info("Filter max age <=%d days: %d kept / %d removed",
                max_age_days, len(posts1), stats["removed_too_old"])

    # --- 2. Min engagement per tier ---
    posts2 = []
    for p in posts1:
        tier = p.get("keyword_tier", "tier1")
        if tier == "tier1":
            min_eng = config.client.collection.min_engagement_tier1
        else:
            min_eng = config.client.collection.min_engagement_tier2
        likes = p.get("likes_count", 0) or 0
        comments = p.get("comments_count", 0) or 0
        total_eng = likes + comments
        if total_eng < min_eng:
            stats["removed_low_engagement"] += 1
            continue
        posts2.append(p)
    logger.info("Filter min engagement: %d kept / %d removed",
                len(posts2), stats["removed_low_engagement"])

    # --- 3. Duplicate text detection (prefix match) ---
    seen_prefixes = set()
    posts3 = []
    for p in posts2:
        text = (p.get("text") or "").strip()
        prefix = text[:80].lower()
        if prefix in seen_prefixes:
            stats["removed_duplicate_text"] += 1
            continue
        seen_prefixes.add(prefix)
        posts3.append(p)
    logger.info("Filter duplicate text: %d kept / %d removed",
                len(posts3), stats["removed_duplicate_text"])

    stats["remaining"] = len(posts3)
    return posts3, stats


def print_filter_funnel(raw_count: int, normalised_count: int,
                        semantic_dropped: int, post_stats: dict):
    """Print a consolidated filter funnel."""
    print()
    print("=" * 70)
    print("FILTER FUNNEL")
    print("=" * 70)
    print(f"  Raw items loaded:                    {raw_count:>5d}")
    print(f"  Normalised:                          {normalised_count:>5d}")
    print(f"  - Removed by semantic filter:        {semantic_dropped:>5d}")
    print(f"    (blocked substrings + min length + semantic similarity)")
    print(f"  - Removed too old (>={config.defaults.max_post_age_days}d):  {post_stats['removed_too_old']:>5d}")
    print(f"  - Removed low engagement:            {post_stats['removed_low_engagement']:>5d}")
    print(f"  - Removed duplicate text:            {post_stats['removed_duplicate_text']:>5d}")
    print(f"  -----------------------------------------")
    print(f"  Remaining after all filters:         {post_stats['remaining']:>5d}")
    print()


def print_ranked_shortlist(posts: list[dict], scores: list[PostScore], limit: int):
    """Print the top-N posts ranked by heuristic score."""
    # Attach scores to posts and sort descending
    ranked = list(zip(posts, scores))
    ranked.sort(key=lambda x: x[1].score, reverse=True)

    # Filter to comment_targets only
    comment_targets = [(p, s) for p, s in ranked if s.post_type == "comment_target"]

    print()
    print("=" * 70)
    print(f"RANKED SHORTLIST — COMMENT TARGETS (top {min(limit, len(comment_targets))})")
    print("=" * 70)

    if not comment_targets:
        print("  (no comment targets after scoring)")
        print()
        return

    for i, (post, sc) in enumerate(comment_targets[:limit], 1):
        text = (post.get("text") or "")[:120].replace("\n", " ")
        print(f"\n  #{i:2d}  ─── score={sc.score:.4f}  f={sc.freshness:.2f}  v={sc.velocity:.2f}  "
              f"r={sc.relevance:.2f}  o={sc.opportunity:.2f}  "
              f"tier={post.get('keyword_tier','?')}")
        print(f"  Author:  {post.get('author_name','?')}")
        print(f"  URL:     {post.get('url','?')}")
        print(f"  Text:    {text}")

    # Summarise all types
    type_counts = {}
    for _, sc in ranked:
        type_counts[sc.post_type] = type_counts.get(sc.post_type, 0) + 1
    print()
    print("  Summary by post_type:")
    for t in ["comment_target", "repost_candidate", "avoid"]:
        count = type_counts.get(t, 0)
        print(f"    {t:20s}: {count:>3d}")
    print()


def main():
    global config  # needed for print_filter_funnel
    config = load_config()
    ensure_client_dirs(config)

    logger.info("=" * 60)
    logger.info("Tier-1 + Tier-2 pipeline run (TEST MODE — no LLM comments)")
    logger.info("Client: %s", config.client_id)
    logger.info("=" * 60)

    # ── Load scratch files ──────────────────────────────────────────────
    scratch_dir = Path(__file__).resolve().parent
    run4_path = scratch_dir / "run-4.json"
    run5_path = scratch_dir / "run-5.json"

    if not run4_path.exists():
        logger.error("File not found: %s", run4_path)
        sys.exit(1)
    if not run5_path.exists():
        logger.error("File not found: %s", run5_path)
        sys.exit(1)

    raw_tier1 = load_scratch_json(str(run4_path))
    raw_tier2 = load_scratch_json(str(run5_path))
    all_raw = raw_tier1 + raw_tier2
    raw_count = len(all_raw)
    logger.info("Loaded %d tier-1 items + %d tier-2 items = %d total raw items",
                len(raw_tier1), len(raw_tier2), raw_count)

    # ── Normalise + tag tiers ──────────────────────────────────────────
    posts = tag_posts_with_tier(raw_tier1, raw_tier2)
    normalised_count = len(posts)

    # ── Build niche embedding ──────────────────────────────────────────
    logger.info("")
    logger.info("-- Phase: Semantic embedding --")
    niche_text = build_niche_embedding_text(config.client.niche)
    niche_embedding = build_niche_embedding(niche_text)
    logger.info("Niche embedding built from %d chars of text", len(niche_text))

    # ── Apply semantic filter (blocked_substrings + min length + similarity) ──
    logger.info("")
    logger.info("-- Phase: Semantic filter --")
    semantic_posts, semantic_dropped = apply_semantic_filter(posts, niche_embedding, config)

    # ── Apply remaining filters (age + engagement + dedup) ─────────────
    logger.info("")
    logger.info("-- Phase: Content filters --")
    filtered_posts, filter_stats = apply_post_filters(semantic_posts, config)

    # ── Print funnel ───────────────────────────────────────────────────
    print_filter_funnel(raw_count, normalised_count, semantic_dropped, filter_stats)

    # ── Score + rank ───────────────────────────────────────────────────
    logger.info("")
    logger.info("-- Phase: Post scoring --")
    scores = [score_post(p, config) for p in filtered_posts]

    # Print ranked shortlist
    limit_comments = config.client.action_limits.comments_per_day
    print_ranked_shortlist(filtered_posts, scores, limit_comments)

    # ── Profiles (empty from this data) ────────────────────────────────
    profiles = []
    keywords = list(config.client.keywords.tier1_direct) + list(config.client.keywords.tier2_lateral)
    profiles = dedup_profiles(profiles)
    profiles = score_profiles(profiles, keywords, config=config)

    # ── SKIP LLM ───────────────────────────────────────────────────────
    logger.info("")
    logger.info("-- Phase: Generate Content (SKIPPED — test mode) --")
    logger.info("  Assigning dummy comment variants to %d posts for planning purposes", len(filtered_posts))
    comments_map = {}
    for post in filtered_posts:
        post_id = post.get("id", "")
        comments_map[post_id] = [{"text": "[TEST MODE — no LLM comment generated]"}]

    # ── Plan ───────────────────────────────────────────────────────────
    logger.info("")
    logger.info("-- Phase: Plan (limit: %d comments) --", limit_comments)
    plan = build_daily_plan(
        posts=filtered_posts,
        profiles=profiles,
        comments_map=comments_map,
        config=config,
    )

    # Print selection results
    comment_actions = [a for a in plan.get("actions", []) if a["type"] == "comment"]
    print()
    print("=" * 70)
    print(f"SELECTED POSTS FOR COMMENTS (limit: {limit_comments}, selected: {len(comment_actions)})")
    print("=" * 70)
    if comment_actions:
        for i, act in enumerate(comment_actions, 1):
            print(f"\n--- Comment #{i} (priority={act['priority']}) ---")
            print(f"  Author:    {act['author_name']}")
            print(f"  URL:       {act['url']}")
            print(f"  Preview:   {act['post_preview'][:150]}")
    else:
        print("  (no comment actions in plan)")

    print()
    print(f"Total actions planned: {len(plan['actions'])}")

    print()
    logger.info("Pipeline complete (test mode).")


if __name__ == "__main__":
    main()