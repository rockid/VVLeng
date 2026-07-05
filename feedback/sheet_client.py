"""Thin gspread wrapper for the VVLeng feedback Google Sheet.

Writes daily_log and run_costs rows at the end of each pipeline run;
reads daily_log + engagement for the end-of-run checklist.

Design constraints:
- Fail-soft: any sheet error logs a warning and falls back to a local
  CSV so the pipeline never blocks on feedback infra.
- Batched: one API call per tab per run (not per row).
- Double-append guard: if rows for (client, date) already exist in the
  tab, the append is skipped with a warning (reruns must not duplicate).
- Skipped entirely under dry_run (zero-network guarantee).
"""

import csv
import logging
import os
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

_DAILY_LOG_TAB = "daily_log"
_RUN_COSTS_TAB = "run_costs"
_ENGAGEMENT_TAB = "engagement"
_WEEKLY_TAB = "weekly"

# Columns written by the pipeline in daily_log (A-N = indices 0-13).
# O-Q are operator-filled and left blank on append.
_DAILY_LOG_PIPELINE_COLS = 14   # A through N
_DAILY_LOG_TOTAL_COLS = 17      # A through Q

# Dedup key columns in daily_log: B (client, 0-based index 1) and A (date, 0).
_DL_COL_DATE = 0
_DL_COL_CLIENT = 1

# Dedup key in run_costs: A (run_date, 0-based 0) and B (client, 1).
_RC_COL_DATE = 0
_RC_COL_CLIENT = 1


def _get_client(config) -> Optional[object]:
    """Open the gspread client; return None if unconfigured or on error."""
    key_path = os.getenv("GSHEET_SERVICE_ACCOUNT_JSON", "")
    sheet_id = os.getenv("GSHEET_FEEDBACK_ID", "")
    if not key_path or not sheet_id:
        return None, None
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(key_path, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        return gc, sh
    except Exception as e:
        logger.warning("feedback: could not open Google Sheet: %s", e)
        return None, None


def _fallback_csv(filename: str, rows: list[list], header: list[str]) -> None:
    """Write rows to a local fallback CSV when the sheet is unreachable."""
    try:
        with open(filename, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        logger.info("feedback: fallback written to %s", filename)
    except Exception as e:
        logger.warning("feedback: fallback CSV write also failed: %s", e)


def _existing_action_ids(ws, date_str: str, client: str,
                         date_col: int, client_col: int,
                         action_id_col: int) -> set[str]:
    """Return the set of action_ids already in the sheet for (date, client)."""
    try:
        all_rows = ws.get_all_values()
        ids: set[str] = set()
        for row in all_rows[1:]:
            if len(row) > max(date_col, client_col, action_id_col):
                if row[date_col] == date_str and row[client_col] == client:
                    ids.add(row[action_id_col])
        return ids
    except Exception:
        return set()


def _already_exists(ws, date_str: str, client: str,
                    date_col: int, client_col: int) -> bool:
    """Return True if any data row matches (date, client) — used by run_costs."""
    try:
        all_rows = ws.get_all_values()
        for row in all_rows[1:]:
            if (len(row) > max(date_col, client_col)
                    and row[date_col] == date_str
                    and row[client_col] == client):
                return True
    except Exception:
        pass
    return False


def append_daily_log(rows: list[list], config, fallback_dir: str = ".") -> None:
    """
    Append pipeline-filled daily_log rows (cols A-N per row; O-Q left blank)
    to the feedback sheet.

    Each row in ``rows`` must be a 14-element list matching the pipeline cols:
    [date, client, action_id, post_url, author_name, author_tier,
     rank, post_date, quality_score, source_keywords,
     variant_1, variant_2, variant_3, judge_confidence]

    Skipped (with warning) if rows for this client+date already exist.
    Falls back to a local CSV on any sheet error.
    """
    if not rows:
        return

    date_str = rows[0][_DL_COL_DATE] if rows else date.today().isoformat()
    client_str = rows[0][_DL_COL_CLIENT] if rows else ""

    _gc, sh = _get_client(config)
    if sh is None:
        _fallback_csv(
            os.path.join(fallback_dir, f"feedback_fallback_{date_str}.csv"),
            rows,
            ["date","client","action_id","post_url","author_name","author_tier",
             "rank","post_date","quality_score","source_keywords",
             "variant_1","variant_2","variant_3","judge_confidence"],
        )
        return

    try:
        ws = sh.worksheet(_DAILY_LOG_TAB)
        # Per-action_id dedup: skip only the individual rows already present,
        # so a --top-n all regen can append the new rows without duplicating the
        # already-appended top-30.
        _DL_COL_ACTION_ID = 2
        existing = _existing_action_ids(
            ws, date_str, client_str, _DL_COL_DATE, _DL_COL_CLIENT, _DL_COL_ACTION_ID
        )
        new_rows = [r for r in rows
                    if len(r) > _DL_COL_ACTION_ID and r[_DL_COL_ACTION_ID] not in existing]
        if not new_rows:
            logger.warning(
                "feedback: all %d rows for %s / %s already in daily_log — skipping",
                len(rows), client_str, date_str,
            )
            return
        if existing:
            logger.info(
                "feedback: %d rows already exist, appending %d new rows for %s / %s",
                len(existing), len(new_rows), client_str, date_str,
            )
        # Pad each row to 17 cols (O-Q blank for operator)
        padded = [r + [""] * (_DAILY_LOG_TOTAL_COLS - len(r)) for r in new_rows]
        ws.append_rows(padded, value_input_option="USER_ENTERED")
        logger.info("feedback: appended %d rows to daily_log", len(padded))
    except Exception as e:
        logger.warning("feedback: daily_log append failed, writing fallback: %s", e)
        _fallback_csv(
            os.path.join(fallback_dir, f"feedback_fallback_{date_str}.csv"),
            rows,
            ["date","client","action_id","post_url","author_name","author_tier",
             "rank","post_date","quality_score","source_keywords",
             "variant_1","variant_2","variant_3","judge_confidence"],
        )


def append_run_cost(row: list, config, fallback_dir: str = ".") -> None:
    """
    Append one run_costs row:
    [run_date, client, posts_collected, max_posts_per_kw,
     n_keywords, apify_cost_usd, llm_cost_note]

    apify_cost_usd is left blank (operator fills from console).
    Skipped if a row for this client+date already exists.
    """
    if not row:
        return

    date_str = row[_RC_COL_DATE]
    client_str = row[_RC_COL_CLIENT]

    _gc, sh = _get_client(config)
    if sh is None:
        return  # no fallback needed — run_costs is a single reference row

    try:
        ws = sh.worksheet(_RUN_COSTS_TAB)
        if _already_exists(ws, date_str, client_str, _RC_COL_DATE, _RC_COL_CLIENT):
            logger.warning(
                "feedback: run_costs already has a row for %s / %s — skipping",
                client_str, date_str,
            )
            return
        ws.append_rows([row], value_input_option="USER_ENTERED")
        logger.info("feedback: appended run_costs row for %s", date_str)
    except Exception as e:
        logger.warning("feedback: run_costs append failed: %s", e)


def load_exclusions(client: str, config, author_cooldown_days: int = 7) -> dict:
    """
    Read daily_log and return two exclusion sets for the next run:

    - ``commented_post_urls``: URLs where ``posted_at`` is non-empty (permanent).
    - ``touched_authors``: author_name values where ``posted_at`` is non-empty
      and within ``author_cooldown_days`` of today (cooldown window).

    Fail-soft: on any error (sheet unreachable, missing cols) emits a loud
    WARNING and returns empty sets so the pipeline runs without exclusions.

    The cooldown uses ``posted_at`` (when the operator commented), not the
    run date, so the window is accurate even across multi-day backlogs.
    """
    empty = {"commented_post_urls": set(), "touched_authors": set()}
    _gc, sh = _get_client(config)
    if sh is None:
        logger.warning(
            "feedback: load_exclusions — sheet unreachable; running WITHOUT exclusions"
        )
        return empty
    try:
        ws = sh.worksheet(_DAILY_LOG_TAB)
        all_rows = ws.get_all_values()
        if len(all_rows) < 2:
            return empty
        header = all_rows[0]
        try:
            date_col = header.index("date")
            client_col = header.index("client")
            url_col = header.index("post_url")
            author_col = header.index("author_name")
            posted_at_col = header.index("posted_at")
        except ValueError as e:
            logger.warning("feedback: load_exclusions — column missing (%s); no exclusions", e)
            return empty

        cutoff = (date.today() - timedelta(days=author_cooldown_days)).isoformat()
        commented_urls: set[str] = set()
        touched_authors: set[str] = set()

        for row in all_rows[1:]:
            if len(row) <= max(date_col, client_col, url_col, author_col, posted_at_col):
                continue
            if row[client_col] != client:
                continue
            posted_at = row[posted_at_col].strip()
            if not posted_at:
                continue
            url = row[url_col].strip()
            if url:
                commented_urls.add(url)
            author = row[author_col].strip()
            if author and posted_at >= cutoff:
                touched_authors.add(author)

        logger.info(
            "feedback: exclusions loaded — %d commented URLs, %d authors in cooldown",
            len(commented_urls), len(touched_authors),
        )
        return {"commented_post_urls": commented_urls, "touched_authors": touched_authors}

    except Exception as e:
        logger.warning(
            "feedback: load_exclusions failed (%s); running WITHOUT exclusions", e
        )
        return empty


def read_daily_log(since_date: str, config) -> list[dict]:
    """
    Return daily_log rows (as dicts) with date >= since_date (YYYY-MM-DD).
    Returns [] on any error so callers can degrade gracefully.
    """
    _gc, sh = _get_client(config)
    if sh is None:
        return []
    try:
        ws = sh.worksheet(_DAILY_LOG_TAB)
        all_rows = ws.get_all_values()
        if len(all_rows) < 2:
            return []
        header = all_rows[0]
        return [
            dict(zip(header, row))
            for row in all_rows[1:]
            if row and row[_DL_COL_DATE] >= since_date
        ]
    except Exception as e:
        logger.warning("feedback: read_daily_log failed: %s", e)
        return []


def print_end_of_run_checklist(config, run_date: Optional[str] = None) -> None:
    """
    Read daily_log + engagement + weekly and print an unmissable checklist:

    - Rows from previous dates where 'worked' is empty → "unworked sheet rows"
    - Posted comments aged 3-4 days with no matching engagement row
      → "engagement tally due"
    - Last weekly row older than 7 days → "weekly stats due"

    Fails silently if the sheet is unreachable (no noise on successful runs
    that happen to be offline).
    """
    today = run_date or date.today().isoformat()

    _gc, sh = _get_client(config)
    if sh is None:
        return

    try:
        issues: list[str] = []

        # ── Unworked rows from previous dates ──────────────────────────────
        # A row is "unworked" when posted_at AND reject_reason are both empty.
        try:
            dl_ws = sh.worksheet(_DAILY_LOG_TAB)
            dl_rows = dl_ws.get_all_values()
            if len(dl_rows) > 1:
                header = dl_rows[0]
                try:
                    date_idx = header.index("date")
                    posted_at_idx = header.index("posted_at")
                    reject_idx = header.index("reject_reason")
                except ValueError:
                    date_idx, posted_at_idx, reject_idx = 0, 16, 15
                unworked = [
                    r for r in dl_rows[1:]
                    if len(r) > max(date_idx, posted_at_idx, reject_idx)
                    and r[date_idx] < today
                    and not r[posted_at_idx].strip()
                    and not r[reject_idx].strip()
                ]
                if unworked:
                    issues.append(
                        f"  ⚠  {len(unworked)} unworked sheet row(s) from previous dates"
                    )
        except Exception as e:
            logger.debug("feedback checklist: daily_log read error: %s", e)

        # ── Engagement tally due (comments posted 3-4 days ago) ───────────
        try:
            dl_ws = sh.worksheet(_DAILY_LOG_TAB)
            dl_rows = dl_ws.get_all_values()
            eng_ws = sh.worksheet(_ENGAGEMENT_TAB)
            eng_rows = eng_ws.get_all_values()

            eng_urls = set()
            if len(eng_rows) > 1:
                try:
                    url_idx = eng_rows[0].index("post_url")
                    eng_urls = {r[url_idx] for r in eng_rows[1:] if len(r) > url_idx and r[url_idx]}
                except ValueError:
                    eng_urls = {r[1] for r in eng_rows[1:] if len(r) > 1}

            if len(dl_rows) > 1:
                header = dl_rows[0]
                try:
                    date_idx = header.index("date")
                    url_idx = header.index("post_url")
                    posted_at_idx = header.index("posted_at")
                except ValueError:
                    date_idx, url_idx, posted_at_idx = 0, 3, 16

                from datetime import datetime
                today_dt = datetime.fromisoformat(today)
                tally_due = []
                for r in dl_rows[1:]:
                    if len(r) <= max(date_idx, url_idx, posted_at_idx):
                        continue
                    row_date = r[date_idx]
                    posted_at = r[posted_at_idx].strip()
                    url = r[url_idx]
                    if not posted_at or not row_date or not url:
                        continue
                    try:
                        age_days = (today_dt - datetime.fromisoformat(row_date)).days
                    except ValueError:
                        continue
                    if 3 <= age_days <= 4 and url not in eng_urls:
                        tally_due.append(row_date)

                if tally_due:
                    from collections import Counter
                    for d, n in Counter(tally_due).items():
                        issues.append(
                            f"  ⚠  engagement tally due: {n} comment(s) posted {d} have no engagement row yet"
                        )
        except Exception as e:
            logger.debug("feedback checklist: engagement check error: %s", e)

        # ── Weekly stats overdue ───────────────────────────────────────────
        try:
            wk_ws = sh.worksheet(_WEEKLY_TAB)
            wk_rows = wk_ws.get_all_values()
            if len(wk_rows) > 1:
                last_week = wk_rows[-1][0]  # week_start col A
                if last_week:
                    from datetime import datetime
                    age = (datetime.fromisoformat(today) - datetime.fromisoformat(last_week)).days
                    if age > 7:
                        issues.append(f"  ⚠  weekly stats due (last entry: {last_week})")
            else:
                issues.append("  ⚠  weekly stats tab is empty — add this week's numbers")
        except Exception as e:
            logger.debug("feedback checklist: weekly check error: %s", e)

        if issues:
            print()
            print("── Feedback sheet checklist ──────────────────────────────")
            for msg in issues:
                print(msg)
            print("──────────────────────────────────────────────────────────")
        else:
            logger.info("feedback: checklist clean — nothing overdue")

    except Exception as e:
        logger.warning("feedback: end-of-run checklist failed: %s", e)
