#!/usr/bin/env python3
"""
VVLeng — LinkedIn Engagement Pipeline
======================================
Orchestrates the full pipeline: collect → process → generate → plan.

Usage:
    python run_pipeline.py                                  # Run full pipeline (default client)
    python run_pipeline.py --client Joinee                  # Override client
    python run_pipeline.py --skip-collect                   # Skip Apify collection
    python run_pipeline.py --skip-llm                       # Skip LLM comment generation
    python run_pipeline.py --dry-run                        # Print plan but don't persist
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


def main():
    parser = argparse.ArgumentParser(description="VVLeng LinkedIn Engagement Pipeline")
    parser.add_argument("--skip-collect", action="store_true", help="Skip Apify data collection")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM comment generation")
    parser.add_argument("--dry-run", action="store_true", help="Print plan but don't persist")
    parser.add_argument("--client", type=str, default=None,
                        help="Client ID (overrides config.yaml active_client)")
    parser.add_argument("--keywords", type=str, default=None,
                        help="Comma-separated keywords (overrides client config)")
    args = parser.parse_args()

    # ── Load config (three-layer) ──────────────────────────────────────────
    from config_loader import load_config, ensure_client_dirs

    config = load_config(client_id_override=args.client)
    ensure_client_dirs(config)

    logger.info("=" * 60)
    logger.info("VVLeng Pipeline — %s", datetime.utcnow().isoformat())
    logger.info("Client: %s", config.client_id)
    logger.info("Flags: skip_collect=%s, skip_llm=%s, dry_run=%s",
                args.skip_collect, args.skip_llm, args.dry_run)
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

    # 1. COLLECT
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

    # 2. PROCESS (always runs if we have data)
    logger.info("── Phase 2: Process ──")
    from processor.dedup import dedup_profiles
    from processor.scorer import score_profiles

    profiles = dedup_profiles(profiles)
    profiles = score_profiles(profiles, keywords, config=config)
    logger.info("Scored profiles: %d total", len(profiles))

    # 3. CONTENT (LLM comment generation)
    comments_map: dict[str, list[dict]] = {}
    if not args.skip_llm and posts:
        logger.info("── Phase 3: Generate Content ──")
        from content.comment_gen import generate_comments

        niche_desc = config.client.niche_description or keywords_str

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
                    config=config,
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
        config=config,
    )

    if args.dry_run:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
    else:
        path = write_plan(plan, plans_dir=config.plans_dir)
        logger.info("Plan saved to %s", path)

    # Summary
    logger.info("=" * 60)
    logger.info("Pipeline complete.")
    logger.info("  Client         : %s", config.client_id)
    logger.info("  Posts collected : %d", len(posts))
    logger.info("  Profiles scored : %d", len(profiles))
    logger.info("  Comments gen'd  : %d", sum(len(v) for v in comments_map.values()))
    logger.info("  Actions planned : %d", len(plan.get("actions", [])))
    logger.info("=" * 60)


if __name__ == "__main__":
    main()