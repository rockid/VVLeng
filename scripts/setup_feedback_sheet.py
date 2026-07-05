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


_NAV_ROWS = [
    ["VVLeng Feedback Sheet — Quick Reference"],
    [],
    ["TABS", "FILLED BY", "PURPOSE"],
    ["nav", "—", "This reference card"],
    ["daily_log", "Pipeline (A–L)  /  You (M–Q)", "One row per comment target per run. Fill M–Q after each session."],
    ["engagement", "You", "Fill at +72 h for every comment you posted."],
    ["weekly", "You", "One row every Monday with LinkedIn Analytics numbers."],
    ["run_costs", "Pipeline + You (F)", "One row per collection run. Fill apify_cost_usd from the Apify console."],
    [],
    ["DAILY LOG — COLUMNS AT A GLANCE"],
    ["Col", "Name", "Who fills", "Notes"],
    ["A", "date", "pipeline", "Run date YYYY-MM-DD"],
    ["B", "client", "pipeline", "e.g. Joinee"],
    ["C", "action_id", "pipeline", "act_001 … act_030"],
    ["D", "post_url", "pipeline", "LinkedIn post URL"],
    ["E", "author_name", "pipeline", ""],
    ["F", "author_tier", "pipeline", "tier1 / tier2"],
    ["G", "rank", "pipeline", "1–30 position in today's sheet"],
    ["H", "source_keywords", "pipeline", "All keywords that returned this post (comma-joined)"],
    ["I", "variant_1", "pipeline", "Judge's top pick"],
    ["J", "variant_2", "pipeline", ""],
    ["K", "variant_3", "pipeline", ""],
    ["L", "judge_confidence", "pipeline", "1–5. 5 = post blindly; 3 = worth a glance; 1 = rewrite."],
    ["M", "worked", "YOU", "Dropdown: yes / skipped"],
    ["N", "variant_used", "YOU", "Dropdown: 1 / 2 / 3 / edited"],
    ["O", "posted_text", "YOU", "Paste final text if you edited (feeds the future few-shot block)"],
    ["P", "reject_reason", "YOU", "One word if skipped — off-niche, quality, timing, …"],
    ["Q", "posted_at", "YOU", "Date posted (if worked = yes)"],
    [],
    ["DAILY ROUTINE (5 min)"],
    ["After commenting:", "Open daily_log → fill M–Q for each post you acted on."],
    ["At +72 h:", "Open engagement → add one row per posted comment."],
    ["Every Monday:", "Open weekly → add last week's LinkedIn Analytics numbers."],
    [],
    ["AMBER ROWS"],
    ["A row turns amber when date < today AND worked (col M) is empty — backlog reminder."],
    [],
    ["END-OF-RUN CHECKLIST"],
    ["The pipeline prints a checklist block at exit. Three signals:"],
    ["⚠ unworked sheet rows", "Previous-date rows with col M blank."],
    ["⚠ engagement tally due", "Comments posted 3–4 days ago with no engagement row yet."],
    ["⚠ weekly stats due", "Last weekly row is older than 7 days."],
    [],
    ["SETUP"],
    ["Run scripts/setup_feedback_sheet.py any time — it is idempotent (won't overwrite data)."],
    ["Credentials: GSHEET_SERVICE_ACCOUNT_JSON and GSHEET_FEEDBACK_ID in .env"],
    ["Full reference: docs/FEEDBACK_SHEET.md"],
]


def _ensure_nav_tab(sh) -> None:
    """Create (or refresh) the nav reference-card tab — always rewritten so
    it stays in sync with the schema even if setup is re-run months later."""
    existing = {ws.title: ws for ws in sh.worksheets()}
    if "nav" in existing:
        nav_ws = existing["nav"]
        logger.info("Tab 'nav' exists — refreshing content")
        nav_ws.clear()
    else:
        # Insert as the first tab so it's always visible on open
        nav_ws = sh.add_worksheet(title="nav", rows=60, cols=6)
        sh.reorder_worksheets([nav_ws] + [ws for ws in sh.worksheets() if ws.title != "nav"])
        logger.info("Created tab 'nav'")

    nav_ws.update(range_name="A1", values=_NAV_ROWS)

    # Format title row bold + slightly larger
    try:
        sh.batch_update({"requests": [
            {
                "repeatCell": {
                    "range": {"sheetId": nav_ws.id, "startRowIndex": 0, "endRowIndex": 1},
                    "cell": {"userEnteredFormat": {
                        "textFormat": {
                            "bold": True, "fontSize": 13,
                            "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        },
                        "backgroundColor": {"red": 0.17, "green": 0.24, "blue": 0.31},
                    }},
                    "fields": "userEnteredFormat(textFormat,backgroundColor)",
                }
            },
            # Section header rows bold
            *[
                {
                    "repeatCell": {
                        "range": {"sheetId": nav_ws.id,
                                  "startRowIndex": i, "endRowIndex": i + 1,
                                  "startColumnIndex": 0, "endColumnIndex": 1},
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                        "fields": "userEnteredFormat(textFormat)",
                    }
                }
                for i, row in enumerate(_NAV_ROWS)
                if row and len(row) == 1 and row[0] and row[0] != _NAV_ROWS[0][0]
            ],
            # "Who fills = YOU" rows highlighted light blue
            *[
                {
                    "repeatCell": {
                        "range": {"sheetId": nav_ws.id,
                                  "startRowIndex": i, "endRowIndex": i + 1},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.83, "green": 0.91, "blue": 0.98}
                        }},
                        "fields": "userEnteredFormat(backgroundColor)",
                    }
                }
                for i, row in enumerate(_NAV_ROWS)
                if len(row) >= 3 and row[2] == "YOU"
            ],
            # Auto-resize col A
            {"autoResizeDimensions": {
                "dimensions": {"sheetId": nav_ws.id, "dimension": "COLUMNS",
                               "startIndex": 0, "endIndex": 4}
            }},
        ]})
        logger.info("Nav tab formatting applied")
    except Exception as e:
        logger.warning("Nav tab formatting failed (non-fatal): %s", e)


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
    _ensure_nav_tab(sh)
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
