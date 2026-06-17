#!/usr/bin/env python3
"""
VVLeng — LinkedIn Engagement Pipeline
======================================
Orchestrates the full pipeline: collect → process (semantic filter + content filters + score + rank) → generate → plan.

Usage:
    python run_pipeline.py                                  # Run full pipeline (default client)
    python run_pipeline.py --client Joinee                  # Override client
    python run_pipeline.py --skip-collect                   # Skip Apify collection
    python run_pipeline.py --skip-semantic                  # Skip semantic filter + content filters
    python run_pipeline.py --skip-llm                       # Skip LLM comment generation
    python run_pipeline.py --dry-run                        # Print plan but don't persist
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta, timezone
from typing import Optional

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


def tag_posts_by_keyword_tier(posts: list[dict], config) -> list[dict]:
    """
    Tag each post with its ``keyword_tier`` by matching post text against
    the configured tier1 and tier2 keyword lists.

    A post is tier-1 if its text (or author_headline) contains any tier1_direct
    keyword substring. Otherwise defaults to tier2.

    Returns the same list with a ``keyword_tier`` key added to each post.
    """
    tier1_kw = list(config.client.keywords.tier1_direct)
    tier2_kw = list(config.client.keywords.tier2_lateral)

    tier1_kw_lower = [kw.lower() for kw in tier1_kw]
    tier2_kw_lower = [kw.lower() for kw in tier2_kw]

    def _matches(text: str, keywords: list[str]) -> bool:
        text_lower = text.lower()
        for kw in keywords:
            if " NOT " in kw:
                # Complex boolean keyword — skip simple matching, treat as tier2
                continue
            if kw in text_lower:
                return True
        return False

    tagged = []
    for p in posts:
        text = (p.get("text") or "") + " " + (p.get("author_headline") or "")
        if _matches(text, tier1_kw_lower):
            p["keyword_tier"] = "tier1"
        elif _matches(text, tier2_kw_lower):
            p["keyword_tier"] = "tier2"
        else:
            # Default to tier2 (lateral relevance)
            p["keyword_tier"] = "tier2"
        tagged.append(p)

    tier1_count = sum(1 for p in tagged if p["keyword_tier"] == "tier1")
    tier2_count = sum(1 for p in tagged if p["keyword_tier"] == "tier2")
    logger.info("Tagged posts: %d tier-1, %d tier-2", tier1_count, tier2_count)
    return tagged


def apply_semantic_filter(posts: list[dict], niche_embedding: np.ndarray, config) -> tuple[list[dict], int]:
    """
    Apply semantic similarity gate via processor/semantic_filter.passes_filter().
    Returns (kept_posts, dropped_count).
    """
    from processor.semantic_filter import passes_filter

    kept = []
    dropped = 0
    for p in posts:
        passed, score = passes_filter(p, niche_embedding, config)
        if passed:
            kept.append(p)
        else:
            dropped += 1

    logger.info("Semantic filter: %d kept / %d dropped", len(kept), dropped)
    return kept, dropped


def apply_content_filters(posts: list[dict], config) -> tuple[list[dict], dict]:
    """
    Apply post-level content filters NOT covered by the semantic filter.

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
                        semantic_dropped: int, content_stats: dict):
    """Print a consolidated filter funnel to stdout."""
    print()
    print("=" * 70)
    print("FILTER FUNNEL")
    print("=" * 70)
    print(f"  Raw items collected:                {raw_count:>5d}")
    print(f"  Normalised:                         {normalised_count:>5d}")
    print(f"  - Removed by semantic filter:       {semantic_dropped:>5d}")
    print(f"    (blocked substrings + min length + semantic similarity)")
    print(f"  - Removed too old:                  {content_stats['removed_too_old']:>5d}")
    print(f"  - Removed low engagement:           {content_stats['removed_low_engagement']:>5d}")
    print(f"  - Removed duplicate text:           {content_stats['removed_duplicate_text']:>5d}")
    print(f"  -----------------------------------------")
    print(f"  Remaining after all filters:        {content_stats['remaining']:>5d}")
    print()


def print_ranked_shortlist(posts: list[dict], scores: list, limit: int):
    """Print the top-N posts ranked by heuristic score."""
    from processor.post_scorer import PostScore

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

    # Summary by type
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
    parser = argparse.ArgumentParser(description="VVLeng LinkedIn Engagement Pipeline")
    parser.add_argument("--skip-collect", action="store_true", help="Skip Apify data collection")
    parser.add_argument("--skip-semantic", action="store_true",
                        help="Skip semantic filter + content filters (age/engagement/dedup)")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM comment generation")
    parser.add_argument("--dry-run", action="store_true", help="Print plan but don't persist")
    parser.add_argument("--client", type=str, default=None,
                        help="Client ID (overrides config.yaml active_client)")
    parser.add_argument("--keywords", type=str, default=None,
                        help="Comma-separated keywords (overrides client config)")
    args = parser.parse_args()

    # ── Load config (three-layer) ──────────────────────────────────────────
    from config_loader import load_config, ensure_client_dirs, build_niche_embedding_text

    config = load_config(client_id_override=args.client)
    ensure_client_dirs(config)

    logger.info("=" * 60)
    logger.info("VVLeng Pipeline — %s", datetime.utcnow().isoformat())
    logger.info("Client: %s", config.client_id)
    logger.info("Flags: skip_collect=%s, skip_semantic=%s, skip_llm=%s, dry_run=%s",
                args.skip_collect, args.skip_semantic, args.skip_llm, args.dry_run)
    logger.info("=" * 60)

    # ── Determine keywords ─────────────────────────────────────────────────
    # Priority: CLI arg → client_config.seed_keywords → fallback
    keywords_str = args.keywords or ""
    if keywords_str:
        keywords = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]
    else:
        keywords = config.client.seed_keywords or [
            "AI", "machine learning", "data science"
        ]

    # =====================================================================
    # 1. COLLECT
    # =====================================================================
    raw_posts = []
    posts = []
    profiles = []
    if not args.skip_collect:
        logger.info("── Phase 1: Collect ──")
        from collector.apify_client import run_actor, save_raw, build_actor_input
        from collector.normaliser import normalise_posts, normalise_profiles
        from collector.incremental import get_unseen_keywords

        active_keywords = get_unseen_keywords(keywords)

        # Post search actor
        post_actor = config.actors.post_search
        max_posts = config.client.max_posts_per_keyword or config.defaults.max_posts_per_keyword
        actor_input = build_actor_input(post_actor, active_keywords, max_items=max_posts)
        logger.info("Running post-search actor %s...", post_actor)
        raw_posts = run_actor(post_actor, actor_input, timeout_secs=240,
                              config=config)
        save_raw(raw_posts, "posts", raw_dir=config.raw_dir)
        posts = normalise_posts(raw_posts)
        logger.info("Collected %d posts", len(posts))

        # Profile search actor (if configured — skip gracefully if fails)
        profile_actor = config.actors.profile_scraper or ""
        if profile_actor:
            try:
                profile_input = {"keywords": active_keywords, "maxProfiles": 30}
                logger.info("Running profile-search actor %s...", profile_actor)
                raw_profiles = run_actor(profile_actor, profile_input, timeout_secs=240,
                                         config=config)
                save_raw(raw_profiles, "profiles", raw_dir=config.raw_dir)
                profiles = normalise_profiles(raw_profiles)
                logger.info("Collected %d profiles", len(profiles))
            except Exception as e:
                logger.warning("Profile collection skipped (actor unavailable): %s", e)
                profiles = []
    else:
        logger.info("── Phase 1: Collect (SKIPPED) ──")
        # When skipping collection, try to reload previously saved posts
        raw_dir = config.raw_dir
        posts_file = os.path.join(raw_dir, "posts.json")
        if os.path.exists(posts_file):
            with open(posts_file, "r", encoding="utf-8") as f:
                raw_posts_data = json.load(f)
            from collector.normaliser import normalise_posts
            posts = normalise_posts(raw_posts_data)
            logger.info("Reloaded %d posts from %s", len(posts), posts_file)
        else:
            logger.warning("No saved posts found in %s; proceeding with empty posts list", raw_dir)

    raw_count = len(raw_posts)
    normalised_count = len(posts)

    # =====================================================================
    # 2. TAG posts with keyword_tier (tier1 / tier2)
    # =====================================================================
    if posts:
        posts = tag_posts_by_keyword_tier(posts, config)

    # =====================================================================
    # 3. PROCESS — full funnel (semantic filter → content filters → score → rank)
    # =====================================================================
    if not args.skip_semantic and posts:
        logger.info("── Phase 2: Process — Semantic Filter ──")
        from processor.semantic_filter import build_niche_embedding

        # Build niche embedding from client config
        niche_text = build_niche_embedding_text(config.client.niche)
        niche_embedding = build_niche_embedding(niche_text)
        logger.info("Niche embedding built from %d chars of text", len(niche_text))

        # Apply semantic filter
        semantic_posts, semantic_dropped = apply_semantic_filter(posts, niche_embedding, config)

        # Apply content filters (age + engagement + dedup)
        logger.info("── Phase 2: Process — Content Filters ──")
        filtered_posts, content_stats = apply_content_filters(semantic_posts, config)

        # Print filter funnel
        print_filter_funnel(raw_count, normalised_count, semantic_dropped, content_stats)

        # Score + rank
        logger.info("── Phase 2: Process — Scoring + Ranking ──")
        from processor.post_scorer import score_post, PostScore

        scores = [score_post(p, config) for p in filtered_posts]
        limit_comments = config.client.action_limits.comments_per_day
        print_ranked_shortlist(filtered_posts, scores, limit_comments)

        # Only keep top-N comment_targets for LLM generation
        ranked = list(zip(filtered_posts, scores))
        ranked.sort(key=lambda x: x[1].score, reverse=True)
        comment_targets = [(p, s) for p, s in ranked if s.post_type == "comment_target"]
        top_targets = comment_targets[:limit_comments]

        # Build the shortlist: top comment targets + any repost_candidates
        for_llm_posts = [p for p, _ in top_targets]
        repost_candidates = [p for p, s in ranked if s.post_type == "repost_candidate"]
        # Pass ALL filtered posts to the planner (it needs the full list for dedup)
        # but only generate comments for the top-N targets
    else:
        logger.info("── Phase 2: Process (SKIPPED or no posts) ──")
        filtered_posts = posts
        scores = []
        limit_comments = config.client.action_limits.comments_per_day
        for_llm_posts = posts

    # =====================================================================
    # 4. PROCESS profiles (dedup + score)
    # =====================================================================
    if profiles:
        logger.info("── Phase 2: Process — Profiles ──")
        from processor.dedup import dedup_profiles
        from processor.scorer import score_profiles

        profiles = dedup_profiles(profiles)
        profiles = score_profiles(profiles, keywords, config=config)
        logger.info("Scored profiles: %d total", len(profiles))

    # =====================================================================
    # 5. CONTENT (LLM comment generation — only for top-N filtered posts)
    # =====================================================================
    comments_map: dict[str, list[dict]] = {}
    if not args.skip_llm and for_llm_posts:
        logger.info("── Phase 3: Generate Content (for %d posts) ──", len(for_llm_posts))
        from content.comment_gen import generate_comments

        niche_desc = config.client.niche_description or keywords_str

        for post in for_llm_posts:
            post_id = post.get("id", "")
            post_text = post.get("text", "") or ""
            author_headline = post.get("author_headline", "") or ""
            try:
                comments_map[post_id] = generate_comments(
                    post_text=post_text,
                    author_headline=author_headline,
                    niche=niche_desc,
                    n_variants=3,
                    config=config,
                )
            except Exception as e:
                logger.warning("Comment generation failed for post %s: %s", post_id, e)
                comments_map[post_id] = []
    elif args.skip_llm:
        logger.info("── Phase 3: Generate Content (SKIPPED) ──")
    else:
        logger.info("── Phase 3: Generate Content (no posts to process) ──")

    # =====================================================================
    # 6. PLAN
    # =====================================================================
    logger.info("── Phase 4: Plan ──")
    from planner.daily_plan import build_daily_plan
    from planner.output import write_plan

    plan = build_daily_plan(
        posts=filtered_posts,  # full filtered list for planner
        profiles=profiles,
        comments_map=comments_map,
        config=config,
    )

    if args.dry_run:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
    else:
        path = write_plan(plan, plans_dir=config.plans_dir)
        logger.info("Plan saved to %s", path)

    # Summary
    llm_count = len(comments_map)
    logger.info("=" * 60)
    logger.info("Pipeline complete.")
    logger.info("  Client         : %s", config.client_id)
    logger.info("  Posts collected : %d", len(posts))
    if args.skip_semantic:
        logger.info("  Posts filtered  : (semantic filter skipped)")
    else:
        logger.info("  Posts filtered  : %d", len(filtered_posts))
    logger.info("  LLM generated   : %d posts (%d variants)", llm_count, sum(len(v) for v in comments_map.values()))
    logger.info("  Profiles scored : %d", len(profiles))
    logger.info("  Actions planned : %d", len(plan.get("actions", [])))
    logger.info("=" * 60)


if __name__ == "__main__":
    main()