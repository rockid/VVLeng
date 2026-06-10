"""State management — load/save plan JSON and DB actions."""

import json
import os
import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)

PLANS_DIR = os.getenv("PLANS_DIR", "./data/plans")


def load_plan(plan_date: str | None = None) -> dict:
    """Load the plan JSON for a given date (defaults to today)."""
    if plan_date is None:
        plan_date = date.today().isoformat()
    path = os.path.join(PLANS_DIR, f"{plan_date}_plan.json")
    if not os.path.exists(path):
        logger.warning("Plan file not found: %s", path)
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def update_action_status(
    plan: dict,
    action_id: str,
    new_status: str,
    feedback: dict | None = None,
) -> dict:
    """
    Update the status of an action in the plan dict and persist.

    Args:
        plan: The plan dict (mutated in place).
        action_id: The action_id to update.
        new_status: One of "suggested", "executed", "skipped", "failed".
        feedback: Optional feedback dict (e.g. {"connection_accepted": true}).

    Returns:
        The updated plan dict.
    """
    for action in plan.get("actions", []):
        if action["action_id"] == action_id:
            action["status"] = new_status
            if feedback:
                action["feedback"] = feedback
            break

    # Persist to disk
    plan_date = plan.get("date", date.today().isoformat())
    path = os.path.join(PLANS_DIR, f"{plan_date}_plan.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    logger.info("Action %s → %s (feedback: %s)", action_id, new_status, feedback)
    return plan