"""Apify actor runner — trigger, poll, download."""

import os
import time
import json
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

APIFY_BASE = "https://api.apify.com/v2"
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
MAX_RETRIES = 3
RETRY_BACKOFF_SECS = 60


class ApifyError(Exception):
    """Raised on persistent Apify actor failure."""
    pass


def run_actor(actor_id: str, input_payload: dict, timeout_secs: int = 300) -> list[dict]:
    """
    Trigger an Apify actor, poll until finished (or timeout), return dataset items.
    Raises ApifyError after MAX_RETRIES attempts.
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return _run_actor_once(actor_id, input_payload, timeout_secs)
        except ApifyError as e:
            last_error = e
            logger.warning("Actor %s attempt %d/%d failed: %s", actor_id, attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECS)
    raise ApifyError(f"Actor {actor_id} failed after {MAX_RETRIES} attempts: {last_error}")


def _run_actor_once(actor_id: str, input_payload: dict, timeout_secs: int) -> list[dict]:
    token = APIFY_API_TOKEN
    if not token:
        raise ApifyError("APIFY_API_TOKEN not set")

    # 1. Start the actor
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{APIFY_BASE}/acts/{actor_id}/runs",
            params={"token": token},
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
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{APIFY_BASE}/actor-runs/{run_id}",
                params={"token": token},
            )
            if resp.status_code != 200:
                raise ApifyError(f"Failed to poll run {run_id}: {resp.status_code}")
            status = resp.json()["data"]["status"]

        if status == "SUCCEEDED":
            logger.info("Actor run %s succeeded", run_id)
            return download_dataset(dataset_id)
        elif status in ("FAILED", "TIMED-OUT", "ABORTED"):
            raise ApifyError(f"Actor run {run_id} ended with status={status}")

    raise ApifyError(f"Actor run {run_id} timed out after {timeout_secs}s")


def download_dataset(dataset_id: str) -> list[dict]:
    """Download all items from a dataset."""
    token = APIFY_API_TOKEN
    items: list[dict] = []
    offset = 0
    limit = 1000

    with httpx.Client(timeout=60) as client:
        while True:
            resp = client.get(
                f"{APIFY_BASE}/datasets/{dataset_id}/items",
                params={"token": token, "offset": offset, "limit": limit, "format": "json"},
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


def save_raw(data: list[dict], filename: str, raw_dir: str = "./data/raw"):
    """Save raw Apify output to a timestamped JSON file."""
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(raw_dir, f"{filename}_{timestamp}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Saved raw data to %s", path)
    return path