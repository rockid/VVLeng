"""Emit plan JSON + CSV to disk."""

import json
import logging
import os
from datetime import date

logger = logging.getLogger(__name__)


def write_plan(plan: dict, plans_dir: str = "./data/plans") -> str:
    """
    Write a daily plan dict to a JSON file.

    Args:
        plan: The plan dict (from build_daily_plan).
        plans_dir: Directory to write to.

    Returns:
        Path to the written file.
    """
    os.makedirs(plans_dir, exist_ok=True)
    plan_date = plan.get("date", date.today().isoformat())
    path = os.path.join(plans_dir, f"{plan_date}_plan.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    logger.info("Plan written to %s (%d actions)", path, len(plan.get("actions", [])))
    return path