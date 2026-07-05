# VVLeng Feedback Sheet — Usage Guide

Google Sheet: **VVLeng Feedback** (shared with the service account; ID in `.env`).

## What the pipeline fills automatically

After every live run (`python run_pipeline.py --client Joinee`) the pipeline appends:

- **`daily_log`** — one row per comment target (cols A–L): run date, client, action ID, post URL, author, tier, rank, source keywords, the three comment variants in judge order, and judge confidence. Cols M–Q are left blank for you to fill.
- **`run_costs`** — one row: date, client, posts collected, max posts per keyword, keyword count, and the LLM model used. `apify_cost_usd` is blank — fill it from the Apify console.

Double-append guard is active: reruns on the same date are silently skipped.
Skipped under `--dry-run` (zero-network guarantee).

## Your daily 5-minute routine

### After each commenting session (same day as the run)

Open `daily_log`, find today's rows, and for each post you acted on:

| Col | Field | What to enter |
|---|---|---|
| M | worked | `yes` or `skipped` |
| N | variant_used | `1`, `2`, `3`, or `edited` |
| O | posted_text | paste the final text if you edited a variant (future few-shot corpus) |
| P | reject_reason | one word if skipped — e.g. `off-niche`, `quality`, `timing` |
| Q | posted_at | date you posted, if `worked = yes` |

Rows where M is empty and the date is past today turn amber automatically — a visual reminder of any backlog.

### At +72 hours (for each comment you posted)

Open the `engagement` tab and add one row per posted comment. Fill it manually for now — a future scraper (I-8) will automate cols C–F.

| Col | Field |
|---|---|
| A | posted_date |
| B | post_url |
| C | likes on your comment |
| D | replies on your comment |
| E | replier profile URLs (comma-joined) |
| F | author_replied (yes/no) |
| G | checked_at (today's date) |
| H | notes |

### Every Monday

Add one row to the `weekly` tab with last week's LinkedIn stats (visible in LinkedIn Analytics):

| Col | Field |
|---|---|
| A | week_start (Monday's date) |
| B | profile_views |
| C | search_appearances |
| D | incoming_connection_requests |
| E | notes |

## End-of-run checklist

The pipeline prints a checklist block at the end of every run:

```
── Feedback sheet checklist ──────────────────────────────
  ⚠  3 unworked sheet row(s) from previous dates
  ⚠  engagement tally due: 2 comment(s) posted 2026-07-02 have no engagement row yet
  ⚠  weekly stats due (last entry: 2026-06-30)
──────────────────────────────────────────────────────────
```

No output means everything is up to date. The checklist reads the live sheet — it is never stale.

## Setup (one-time, already done)

- Google Cloud service account created; Sheets API enabled; JSON key at path in `GSHEET_SERVICE_ACCOUNT_JSON` (.env).
- Sheet ID in `GSHEET_FEEDBACK_ID` (.env).
- `scripts/setup_feedback_sheet.py` created the four tabs with frozen headers, dropdowns, and conditional formatting. Run it again at any time — it is idempotent.
