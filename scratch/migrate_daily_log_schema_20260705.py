"""
One-shot migration: restructure the live daily_log sheet to the new schema,
then backfill post_date and quality_score for existing rows.

OLD schema (17 cols):
  A-G: date, client, action_id, post_url, author_name, author_tier, rank
  H:   source_keywords
  I-K: variant_1, variant_2, variant_3
  L:   judge_confidence
  M:   worked          ← DROP
  N:   variant_used    ← DROP
  O:   posted_text
  P:   reject_reason
  Q:   posted_at

NEW schema (17 cols):
  A-G: date, client, action_id, post_url, author_name, author_tier, rank
  H:   post_date       ← INSERT (empty, then backfill)
  I:   quality_score   ← INSERT (empty, then backfill)
  J:   source_keywords
  K-M: variant_1, variant_2, variant_3
  N:   judge_confidence
  O:   posted_text
  P:   reject_reason
  Q:   posted_at

Steps:
  1. Insert 2 columns at position H (index 7) — shifts old cols right by 2.
  2. Delete the two now-displaced worked and variant_used columns.
  3. Backfill H (post_date) and I (quality_score) from saved run artifacts.

Run once; safe to re-run (migration is idempotent via header check).
"""

import json
import os
import sys
import csv
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import gspread
from google.oauth2.service_account import Credentials

SA_PATH = os.getenv("GSHEET_SERVICE_ACCOUNT_JSON", "")
SHEET_ID = os.getenv("GSHEET_FEEDBACK_ID", "")

ARTIFACTS = {
    "2026-07-05": {
        "raw_json": r"data\Joinee\raw\posts_20260705T071720Z.json",
        "comment_sheet": r"data\Joinee\output\comment_sheet_2026-07-05.csv",
    },
    "2026-06-22": {
        "raw_json": r"data\Joinee\raw\posts_20260622T180303Z.json",
        "comment_sheet": r"data\Joinee\output\comment_sheet_2026-06-22.csv",
    },
}

NEW_HEADERS = [
    "date", "client", "action_id", "post_url", "author_name", "author_tier",
    "rank", "post_date", "quality_score", "source_keywords",
    "variant_1", "variant_2", "variant_3",
    "judge_confidence",
    "posted_text", "reject_reason", "posted_at",
]


def _build_lookup(run_date: str) -> tuple[dict, dict]:
    """Return (url→post_date, url→quality_score) for a given run date."""
    art = ARTIFACTS.get(run_date, {})
    url_to_post_date: dict[str, str] = {}
    url_to_quality: dict[str, str] = {}

    # quality_score from comment sheet rank_score
    cs_path = art.get("comment_sheet", "")
    if cs_path and os.path.exists(cs_path):
        with open(cs_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                url = row.get("post_url", "").strip()
                rs = row.get("rank_score", "").strip()
                if url and rs:
                    try:
                        url_to_quality[url] = str(round(float(rs), 2))
                    except ValueError:
                        pass
        print(f"  quality_score: loaded {len(url_to_quality)} URLs from {cs_path}")
    else:
        print(f"  quality_score: no comment sheet found for {run_date}")

    # post_date from raw Apify JSON (query-matched so we get the actual publish date)
    raw_path = art.get("raw_json", "")
    if raw_path and os.path.exists(raw_path):
        with open(raw_path, encoding="utf-8") as f:
            raw = json.load(f)
        for post in raw:
            url = post.get("linkedinUrl", "").strip()
            dt = (post.get("postedAt") or {}).get("date", "")
            if url and dt:
                url_to_post_date[url] = dt[:10]  # YYYY-MM-DD
        print(f"  post_date: loaded {len(url_to_post_date)} URLs from {raw_path}")
    else:
        print(f"  post_date: no raw JSON found for {run_date}")

    return url_to_post_date, url_to_quality


def main():
    if not SA_PATH or not SHEET_ID:
        print("GSHEET_SERVICE_ACCOUNT_JSON or GSHEET_FEEDBACK_ID not set")
        sys.exit(1)

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SA_PATH, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.worksheet("daily_log")

    # ── Guard: idempotent ────────────────────────────────────────────────────
    current_header = ws.row_values(1)
    if current_header == NEW_HEADERS:
        print("Header already matches new schema — nothing to do.")
        return
    if "post_date" in current_header and "quality_score" in current_header:
        print("post_date and quality_score already present — skipping column surgery.")
        _backfill_only(ws, sh)
        return

    print(f"Current header ({len(current_header)} cols): {current_header}")
    print(f"Migrating to new schema ({len(NEW_HEADERS)} cols)...")

    ws_id = ws.id

    # ── Step 1: Insert 2 columns at index 7 (between rank and source_keywords) ─
    sh.batch_update({"requests": [{
        "insertDimension": {
            "range": {
                "sheetId": ws_id,
                "dimension": "COLUMNS",
                "startIndex": 7,   # 0-based, inserts before column H
                "endIndex": 9,     # insert 2 cols
            },
            "inheritFromBefore": False,
        }
    }]})
    print("Inserted 2 columns at H/I")

    # After insert, old layout is now:
    #   G(6)=rank, H(7)=EMPTY, I(8)=EMPTY, J(9)=source_keywords,
    #   K-M=variants, N=confidence, O=worked, P=variant_used, Q=posted_text,
    #   R=reject_reason, S=posted_at

    # ── Step 2: Delete worked (col O, index 14) then variant_used (col O again) ─
    # Delete highest index first so earlier indices don't shift.
    sh.batch_update({"requests": [
        {"deleteDimension": {
            "range": {"sheetId": ws_id, "dimension": "COLUMNS",
                      "startIndex": 15, "endIndex": 16},  # variant_used (P after first delete)
        }},
    ]})
    sh.batch_update({"requests": [
        {"deleteDimension": {
            "range": {"sheetId": ws_id, "dimension": "COLUMNS",
                      "startIndex": 14, "endIndex": 15},  # worked (O)
        }},
    ]})
    print("Deleted worked and variant_used columns")

    # Verify header
    header_now = ws.row_values(1)
    print(f"Header after surgery ({len(header_now)} cols): {header_now}")

    # ── Step 3: Write correct header row ──────────────────────────────────────
    ws.update(range_name="A1", values=[NEW_HEADERS])
    print("Header written")

    # ── Step 4: Backfill post_date (H) and quality_score (I) ─────────────────
    _backfill_only(ws, sh)


def _backfill_only(ws, sh):
    all_rows = ws.get_all_values()
    header = all_rows[0]
    date_col = header.index("date")
    url_col = header.index("post_url")
    pd_col = header.index("post_date")
    qs_col = header.index("quality_score")

    # Load lookup data per run date
    lookups: dict[str, tuple[dict, dict]] = {}
    for run_date in ARTIFACTS:
        lookups[run_date] = _build_lookup(run_date)

    updates = []
    pd_found = qs_found = pd_miss = qs_miss = 0

    for row_idx, row in enumerate(all_rows[1:], start=2):
        if len(row) <= max(date_col, url_col, pd_col, qs_col):
            continue
        run_date = row[date_col]
        url = row[url_col]
        if not url:
            continue

        pd_val = row[pd_col].strip()
        qs_val = row[qs_col].strip()

        url_to_pd, url_to_qs = lookups.get(run_date, ({}, {}))

        if not pd_val:
            new_pd = url_to_pd.get(url, "")
            if new_pd:
                cell = gspread.utils.rowcol_to_a1(row_idx, pd_col + 1)
                updates.append({"range": cell, "values": [[new_pd]]})
                pd_found += 1
            else:
                pd_miss += 1

        if not qs_val:
            new_qs = url_to_qs.get(url, "")
            if new_qs:
                cell = gspread.utils.rowcol_to_a1(row_idx, qs_col + 1)
                updates.append({"range": cell, "values": [[new_qs]]})
                qs_found += 1
            else:
                qs_miss += 1

    print(f"\nBackfill: post_date {pd_found} found / {pd_miss} missing")
    print(f"Backfill: quality_score {qs_found} found / {qs_miss} missing")

    if updates:
        ws.batch_update(updates)
        print(f"Applied {len(updates)} cell updates")
    else:
        print("Nothing to backfill")


if __name__ == "__main__":
    main()
