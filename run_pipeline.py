#!/usr/bin/env python3
"""
VVLeng — LinkedIn Engagement Pipeline
======================================
Orchestrates the full pipeline: collect → process → generate → plan.

Usage:
    python run_pipeline.py                     # Run full pipeline
    python run_pipeline.py --skip-collect      # Skip Apify collection
    python run_pipeline.py --skip-llm          # Skip LLM comment generation
    python run_pipeline.py --dry-run           # Print plan but don't persist
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")

# ── Imports (lazy to keep startup fast) ──────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="VVLeng LinkedIn Engagement Pipeline")
    parser.add_argument("--skip-collect", action="store_true", help="Skip Apify data collection")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM comment generation")
    parser.add_argument("--dry-run", action="store_true", help="Print plan but don't persist")
    parser.add_argument("--keywords", type=str, default=None,
                        help="Comma-separated keywords (overrides NICHE_KEYWORDS env var)")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("VVLeng Pipeline — %s", datetime.utcnow().isoformat())
    logger.info("Flags: skip_collect=%s, skip_llm=%s, dry_run=%s",
                args.skip_collect, args.skip_llm, args.dry_run)
    logger.info("=" * 60)

    # 1. COLLECT
    posts = []
    profiles = []
    if not args.skip_collect:
        logger.info("── Phase 1: Collect ──")
        from collector.apify_client import run_actor, save_raw
        from collector.normaliser import normalise_posts, normalise_profiles
        from collector.incremental import get_unseen_keywords

        keywords_str = args.keywords or os.environ.get("NICHE_KEYWORDS", "")
        keywords = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]
        if not keywords:
            logger.warning("No NICHE_KEYWORDS set. Using defaults: ['AI', 'machine learning', 'data science']")
            keywords = ["AI", "machine learning", "data science"]

        active_keywords = get_unseen_keywords(keywords)

        # Post search actor
        post_actor = os.environ.get("APIFY_POST_ACTOR_ID", "hFuoO7K77oJk4xFpn")
        actor_input = {"keywords": active_keywords, "maxPosts": 20}
        logger.info("Running post-search actor %s...", post_actor)
        raw_posts = run_actor(post_actor, actor_input, timeout_secs=240)
        save_raw(raw_posts, "posts")
        posts = normalise_posts(raw_posts)
        logger.info("Collected %d posts", len(posts))

        # Profile search actor (if configured)
        profile_actor = os.environ.get("APIFY_PROFILE_ACTOR_ID", "")
        if profile_actor:
            profile_input = {"keywords": active_keywords, "maxProfiles": 30}
            logger.info("Running profile-search actor %s...", profile_actor)
            raw_profiles = run_actor(profile_actor, profile_input, timeout_secs=240)
            save_raw(raw_profiles, "profiles")
            profiles = normalise_profiles(raw_profiles)

    # 2. PROCESS (always runs if we have data)
    logger.info("── Phase 2: Process ──")
    from processor.dedup import dedup_profiles
    from processor.scorer import score_profiles

    niche_keywords_str = args.keywords or os.environ.get("NICHE_KEYWORDS", "AI")
    niche_keywords = [kw.strip() for kw in niche_keywords_str.split(",") if kw.strip()]

    profiles = dedup_profiles(profiles)
    profiles = score_profiles(profiles, niche_keywords)
    logger.info("Scored profiles: %d total", len(profiles))

    # 3. CONTENT (LLM comment generation)
    comments_map: dict[str, list[dict]] = {}
    if not args.skip_llm and posts:
        logger.info("── Phase 3: Generate Content ──")
        from content.comment_gen import generate_comments

        niche_desc = os.environ.get("NICHE_DESCRIPTION", niche_keywords_str)

        for post in posts:
            post_id = post.get("id", "")
            post_text = post.get("text", "") or ""
            author_headline = post.get("author_headline", "") or ""
            try:
                comments_map[post_id] = generate_comments(
                    post_text=post_text,
                    author_headline=author_headline,
                    niche=niche_desc,
                    n_variants=3,
                )
            except Exception as e:
                logger.warning("Comment generation failed for post %s: %s", post_id, e)
                comments_map[post_id] = []

    # 4. PLAN
    logger.info("── Phase 4: Plan ──")
    from planner.daily_plan import build_daily_plan
    from planner.output import write_plan

    plan = build_daily_plan(
        posts=posts,
        profiles=profiles,
        comments_map=comments_map,
    )

    if args.dry_run:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
    else:
        path = write_plan(plan)
        logger.info("Plan saved to %s", path)

    # Summary
    logger.info("=" * 60)
    logger.info("Pipeline complete.")
    logger.info("  Posts collected : %d", len(posts))
    logger.info("  Profiles scored : %d", len(profiles))
    logger.info("  Comments gen'd  : %d", sum(len(v) for v in comments_map.values()))
    logger.info("  Actions planned : %d", len(plan.get("actions", [])))
    logger.info("=" * 60)


if __name__ == "__main__":
    main()