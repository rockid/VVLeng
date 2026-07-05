"""
Backfill source_keywords (col H) in the Google Sheet daily_log tab
for 2026-07-05 Joinee rows.

The live run's comment sheet has no source_keywords column, so those cells
were left blank when rows were retro-appended. The raw Apify JSON for that
day has query.search populated for every post, so we can recover the keywords.

Run once manually — no write to code files.
"""

import json
import sys
import os
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_loader import load_config

TARGET_DATE = "2026-07-05"
RAW_JSON = r"data\Joinee\raw\posts_20260705T071720Z.json"


def build_url_to_keywords(raw_path: str) -> dict[str, list[str]]:
    """Build URL → [keywords] from raw Apify data (accumulates across dupes)."""
    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)
    url_kws: dict[str, list[str]] = defaultdict(list)
    for post in raw:
        url = post.get("linkedinUrl") or ""
        kw = (post.get("query") or {}).get("search") or ""
        if url and kw and kw not in url_kws[url]:
            url_kws[url].append(kw)
    print(f"Built keyword map for {len(url_kws)} unique URLs")
    return dict(url_kws)


def backfill_sheet():
    config = load_config()
    url_to_kws = build_url_to_keywords(RAW_JSON)

    import gspread
    sa_path = os.getenv("GSHEET_SERVICE_ACCOUNT_JSON", "")
    if not sa_path:
        print("GSHEET_SERVICE_ACCOUNT_JSON not set — aborting")
        return
    gc = gspread.service_account(filename=sa_path)
    sh_id = os.getenv("GSHEET_FEEDBACK_ID", "")
    sh = gc.open_by_key(sh_id)
    ws = sh.worksheet("daily_log")

    all_rows = ws.get_all_values()
    header = all_rows[0]
    print("Header:", header[:12])

    try:
        date_col = header.index("date")
        client_col = header.index("client")
        url_col = header.index("post_url")
        kw_col = header.index("source_keywords")
    except ValueError as e:
        print(f"Column not found: {e}")
        return

    updates = []
    found = 0
    missing = 0
    for row_idx, row in enumerate(all_rows[1:], start=2):  # 1-indexed, row 1 is header
        if len(row) <= max(date_col, client_col, url_col, kw_col):
            continue
        if row[date_col] != TARGET_DATE or row[client_col] != "Joinee":
            continue
        if row[kw_col].strip():
            print(f"  Row {row_idx}: already has keywords, skipping")
            continue
        url = row[url_col]
        kws = url_to_kws.get(url, [])
        if kws:
            cell = gspread.utils.rowcol_to_a1(row_idx, kw_col + 1)
            updates.append({"range": cell, "values": [[", ".join(kws)]]})
            found += 1
        else:
            print(f"  Row {row_idx}: URL not in raw data — {url[:70]}")
            missing += 1

    print(f"\n{found} rows to update, {missing} URLs not matched in raw JSON")
    if updates:
        ws.batch_update(updates)
        print("Sheet updated.")


if __name__ == "__main__":
    backfill_sheet()
