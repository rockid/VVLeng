"""Apify actor runner — trigger, poll, download."""

import os
import time
import json
import logging
from typing import Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

APIFY_BASE = "https://api.apify.com/v2"
MAX_RETRIES = 3
RETRY_BACKOFF_SECS = 60


class ApifyError(Exception):
    """Raised on persistent Apify actor failure."""
    pass


def _sanitize_actor_id(actor_id: str) -> str:
    """Apify API requires owner~name format (slash → tilde)."""
    return actor_id.replace("/", "~")


def _auth_headers(token: str) -> dict[str, str]:
    """Bearer-token header for every Apify call, keeping the token out of URLs
    (httpx logs full URLs at INFO level, which would leak a query-param token)."""
    return {"Authorization": f"Bearer {token}"}


_MOCK_MARKER = "[DRY_RUN MOCK]"
_MOCK_POSTS_PER_QUERY = 2  # keeps mock volume bounded regardless of keyword count


def _mock_run_actor(actor_id: str, input_payload: dict) -> list[dict]:
    """
    Fake dataset items shaped like the real harvestapi/linkedin-post-search
    output (see tests/fixtures/sample_post_search.json) — used in dry-run mode
    so the full collect→normalise→filter→rank flow can be exercised for free.
    Every field that downstream code reads is populated; everything else is
    omitted rather than guessed.
    """
    logger.info("DRY_RUN: mocking actor %s — no live Apify call made", actor_id)
    queries = input_payload.get("searchQueries") or input_payload.get("keywords") or ["mock"]
    now = datetime.utcnow()
    items: list[dict] = []
    for query in queries:
        for _ in range(_MOCK_POSTS_PER_QUERY):
            idx = len(items) + 1
            items.append({
                "type": "post",
                "id": f"mock-{idx}",
                "linkedinUrl": f"https://www.linkedin.com/posts/dry-run-mock-{idx}",
                "content": (
                    f"{_MOCK_MARKER} Simulated LinkedIn post body #{idx} used to "
                    "exercise the pipeline without a live Apify call. Lorem ipsum "
                    "dolor sit amet, consectetur adipiscing elit, sed do eiusmod "
                    "tempor incididunt ut labore et dolore magna aliqua."
                ),
                "author": {
                    "id": f"mock-author-{idx}",
                    "name": f"{_MOCK_MARKER} Author {idx}",
                    "publicIdentifier": f"dry-run-mock-author-{idx}",
                    "linkedinUrl": f"https://www.linkedin.com/in/dry-run-mock-author-{idx}",
                    "info": f"{_MOCK_MARKER} Simulated headline",
                },
                "postedAt": {
                    "timestamp": int(now.timestamp() * 1000),
                    "date": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                },
                "postImages": [],
                "engagement": {
                    "id": f"mock-engagement-{idx}",
                    "likes": 11,
                    "comments": 2,
                    "shares": 0,
                },
                "query": {
                    "sortBy": input_payload.get("sortBy", "relevance"),
                    "page": 1,
                    "search": query,
                    "postedLimit": input_payload.get("postedLimit", "week"),
                },
                "_mock": True,
            })
    return items


def run_actor(actor_id: str, input_payload: dict, timeout_secs: int = 300,
              config: Optional[object] = None) -> list[dict]:
    """
    Trigger an Apify actor, poll until finished (or timeout), return dataset items.
    Raises ApifyError after MAX_RETRIES attempts.
    Accepts an optional config object with .apify_token attribute.

    If ``config.dry_run`` is set, returns mocked items instead — no live call,
    no token required.
    """
    if config is not None and getattr(config, "dry_run", False):
        return _mock_run_actor(actor_id, input_payload)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return _run_actor_once(actor_id, input_payload, timeout_secs, config)
        except ApifyError as e:
            last_error = e
            logger.warning("Actor %s attempt %d/%d failed: %s", actor_id, attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECS)
    raise ApifyError(f"Actor {actor_id} failed after {MAX_RETRIES} attempts: {last_error}")


def build_actor_input(actor_id: str, keywords: list[str], max_items: int = 30) -> dict:
    """Build actor-specific input payload from common pipeline parameters.

    Each Apify actor has its own expected JSON schema.  This function maps
    the internal (keyword, count) params to the correct schema per actor.
    Add new actors here as they are integrated.
    """
    safe_id = actor_id.replace("/", "~")

    # harvestapi/linkedin-post-search
    if "harvestapi" in safe_id or "linkedin-post-search" in safe_id:
        return {
            "searchQueries": keywords,
            "sortBy": "relevance",   # most-relevant first (was "date")
            "postedLimit": "week",   # 1-week collection window
            "maxPosts": max_items,   # results per search query
            "scrapeReactions": False,
            "scrapeComments": False,
        }

    # Generic fallback for other actors
    return {"keywords": keywords, "maxItems": max_items}


def _run_actor_once(actor_id: str, input_payload: dict, timeout_secs: int,
                    config: Optional[object] = None) -> list[dict]:
    # Get token from config object, then fallback to env var, then to module-level
    if config and hasattr(config, "apify_token") and config.apify_token:
        token = config.apify_token
    else:
        token = os.getenv("APIFY_API_TOKEN", "")
    if not token:
        raise ApifyError("APIFY_API_TOKEN not set")

    # 1. Start the actor (sanitize ID: harvestapi/linkedin-post-search → harvestapi~linkedin-post-search)
    # Token goes in the Authorization header, never the URL — httpx logs full
    # request URLs at INFO, so a query-param token would leak into run logs.
    safe_id = _sanitize_actor_id(actor_id)
    with httpx.Client(timeout=30, headers=_auth_headers(token)) as client:
        resp = client.post(
            f"{APIFY_BASE}/acts/{safe_id}/runs",
            json=input_payload,
        )
        if resp.status_code not in (200, 201):
            raise ApifyError(f"Failed to start actor {actor_id}: {resp.status_code} {resp.text[:200]}")
        run_data = resp.json()["data"]
        run_id = run_data["id"]
        dataset_id = run_data.get("defaultDatasetId")
        logger.info("Started actor %s — run_id=%s dataset_id=%s", actor_id, run_id, dataset_id)

    # 2. Poll until completed
    started = time.time()
    while time.time() - started < timeout_secs:
        time.sleep(5)
        with httpx.Client(timeout=30, headers=_auth_headers(token)) as client:
            resp = client.get(f"{APIFY_BASE}/actor-runs/{run_id}")
            if resp.status_code != 200:
                raise ApifyError(f"Failed to poll run {run_id}: {resp.status_code}")
            status = resp.json()["data"]["status"]

        if status == "SUCCEEDED":
            logger.info("Actor run %s succeeded", run_id)
            return download_dataset(dataset_id, token=token)
        elif status in ("FAILED", "TIMED-OUT", "ABORTED"):
            raise ApifyError(f"Actor run {run_id} ended with status={status}")

    raise ApifyError(f"Actor run {run_id} timed out after {timeout_secs}s")


def download_dataset(dataset_id: str, token: str = "") -> list[dict]:
    """Download all items from a dataset."""
    token = token or os.getenv("APIFY_API_TOKEN", "")
    if not token:
        raise ApifyError("APIFY_API_TOKEN not set for dataset download")
    items: list[dict] = []
    offset = 0
    limit = 1000

    with httpx.Client(timeout=60, headers=_auth_headers(token)) as client:
        while True:
            resp = client.get(
                f"{APIFY_BASE}/datasets/{dataset_id}/items",
                params={"offset": offset, "limit": limit, "format": "json"},
            )
            if resp.status_code != 200:
                raise ApifyError(f"Failed to download dataset {dataset_id}: {resp.status_code}")
            batch = resp.json()
            if not batch:
                break
            items.extend(batch)
            offset += limit

    logger.info("Downloaded %d items from dataset %s", len(items), dataset_id)
    return items


def save_raw(data: list[dict], filename: str, raw_dir: str = "./data/raw",
             config: Optional[object] = None):
    """Save raw Apify output to a timestamped JSON file."""
    # Use config.raw_dir if provided and raw_dir is default
    if config and hasattr(config, "raw_dir") and config.raw_dir and raw_dir == "./data/raw":
        raw_dir = config.raw_dir
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(raw_dir, f"{filename}_{timestamp}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Saved raw data to %s", path)
    return path