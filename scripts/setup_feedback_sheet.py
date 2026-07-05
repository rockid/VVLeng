"""Idempotent setup for the VVLeng feedback Google Sheet.

Creates the four worksheets if missing, writes frozen header rows, and adds
data-validation dropdowns and conditional formatting. Running twice changes
nothing — existing data rows are never touched.

Usage:
    python scripts/setup_feedback_sheet.py
"""

import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Column headers per tab ──────────────────────────────────────────────────

DAILY_LOG_HEADERS = [
    "date", "client", "action_id", "post_url", "author_name", "author_tier",
    "rank", "source_keywords",
    "variant_1", "variant_2", "variant_3",
    "judge_confidence",
    "worked", "variant_used", "posted_text", "reject_reason", "posted_at",
]

ENGAGEMENT_HEADERS = [
    "posted_date", "post_url", "likes_on_our_comment", "replies_on_our_comment",
    "replier_profile_urls", "author_replied", "checked_at", "notes",
]

WEEKLY_HEADERS = [
    "week_start", "profile_views", "search_appearances",
    "incoming_connection_requests", "notes",
]

RUN_COSTS_HEADERS = [
    "run_date", "client", "posts_collected", "max_posts_per_kw",
    "n_keywords", "apify_cost_usd", "llm_cost_note",
]

TABS = {
    "daily_log":  DAILY_LOG_HEADERS,
    "engagement": ENGAGEMENT_HEADERS,
    "weekly":     WEEKLY_HEADERS,
    "run_costs":  RUN_COSTS_HEADERS,
}


def _col_letter(n: int) -> str:
    """1-based column index → letter(s)."""
    result = ""
    while n:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result


def _ensure_tab(sh, title: str, headers: list[str]):
    """Create worksheet and write header row if not already present."""
    existing = {ws.title: ws for ws in sh.worksheets()}
    if title in existing:
        ws = existing[title]
        logger.info("Tab '%s' already exists — skipping creation", title)
    else:
        ws = sh.add_worksheet(title=title, rows=1000, cols=max(len(headers), 10))
        logger.info("Created tab '%s'", title)

    # Write header only if row 1 is empty (idempotent guard)
    top = ws.row_values(1)
    if not top:
        ws.update(range_name="A1", values=[headers])
        ws.freeze(rows=1)
        logger.info("Wrote headers and froze row 1 on '%s'", title)
    else:
        logger.info("Tab '%s' already has headers — left untouched", title)

    return ws


def _add_dropdown(sh, ws, col_index: int, values: list[str]):
    """Add a strict dropdown data-validation to a column (skipping header)."""
    sh.batch_update({"requests": [{
        "setDataValidation": {
            "range": {
                "sheetId": ws.id,
                "startRowIndex": 1,      # 0-based, row 2 onward
                "startColumnIndex": col_index - 1,
                "endColumnIndex": col_index,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [{"userEnteredValue": v} for v in values],
                },
                "showCustomUi": True,
                "strict": True,
            },
        }
    }]})


def _add_amber_overdue(sh, ws):
    """Amber background on daily_log rows where 'worked' (col M) is empty
    and 'date' (col A) is older than today."""
    sh.batch_update({"requests": [{
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": ws.id, "startRowIndex": 1}],
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": '=AND(A2<>"",A2<TODAY(),M2="")'}],
                    },
                    "format": {
                        "backgroundColor": {"red": 1.0, "green": 0.898, "blue": 0.6}
                    },
                },
            },
            "index": 0,
        }
    }]})


def main():
    import gspread
    from google.oauth2.service_account import Credentials

    key_path = os.getenv("GSHEET_SERVICE_ACCOUNT_JSON", "")
    sheet_id = os.getenv("GSHEET_FEEDBACK_ID", "")
    if not key_path or not sheet_id:
        logger.error("GSHEET_SERVICE_ACCOUNT_JSON or GSHEET_FEEDBACK_ID not set in .env")
        sys.exit(1)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(key_path, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    logger.info("Opened: %s", sh.title)

    # Create / verify all tabs
    daily_ws = _ensure_tab(sh, "daily_log", DAILY_LOG_HEADERS)
    _ensure_tab(sh, "engagement", ENGAGEMENT_HEADERS)
    _ensure_tab(sh, "weekly", WEEKLY_HEADERS)
    _ensure_tab(sh, "run_costs", RUN_COSTS_HEADERS)

    # Remove the default Sheet1 if it's still empty.
    # get_all_values() returns [[]] for a visually-empty sheet (truthy), so
    # flatten and check for any non-empty cell.
    existing = {ws.title: ws for ws in sh.worksheets()}
    if "Sheet1" in existing:
        vals = existing["Sheet1"].get_all_values()
        is_empty = not any(cell for row in vals for cell in row)
        if is_empty:
            sh.del_worksheet(existing["Sheet1"])
            logger.info("Removed empty default 'Sheet1'")
        else:
            logger.info("Sheet1 has data — left untouched")

    # Data-validation dropdowns on daily_log cols M (worked) and N (variant_used)
    # Col M = index 13, Col N = index 14 (1-based)
    try:
        _add_dropdown(sh, daily_ws, col_index=13, values=["yes", "skipped"])
        _add_dropdown(sh, daily_ws, col_index=14, values=["1", "2", "3", "edited"])
        logger.info("Dropdowns set on daily_log cols M and N")
    except Exception as e:
        logger.warning("Could not set dropdowns (non-fatal): %s", e)

    # Amber conditional format on daily_log
    try:
        _add_amber_overdue(sh, daily_ws)
        logger.info("Amber conditional format applied to daily_log")
    except Exception as e:
        logger.warning("Could not set conditional format (non-fatal): %s", e)

    # Summary
    tabs = [ws.title for ws in sh.worksheets()]
    print("\nSetup complete.")
    print("Tabs:", tabs)
    for title in tabs:
        ws = sh.worksheet(title)
        print(f"  {title}: header row = {ws.row_values(1)}")


if __name__ == "__main__":
    main()
