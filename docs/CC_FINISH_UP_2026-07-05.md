# VVLeng — Finish-Up Instructions (2026-07-05, evening)

Context: the session report (commit a0df13e) crossed with three operator
decisions made in parallel. This file supersedes CC_FULL_SHEET_MINI and the
FEEDBACK_INGEST addendum — implement from here. Everything below should land
TODAY: the operator starts working the sheet tonight and the Thursday run
depends on the exclusion read.

**Decisions to absorb:**
1. The comment-runner HTML is RETIRED as the working surface. The Google
   Sheet is the operator cockpit (sortable by recency/rank — the actual need).
2. Sheet must cover ALL gate-eligible posts (81 today), not top-30.
3. Simplified feedback convention: `posted_at` filled = done. No buttons,
   no `worked` column.

---

## Task 1 — Schema update (daily_log)

1. **Add two pipeline-filled columns** after `rank`:
   - `post_date` — the LinkedIn post's publish date (YYYY-MM-DD). If the
     actor gives only relative age, compute run_date − age; note the
     convention in the runbook.
   - `quality_score` — the existing blended rank_score, 2 decimals. Not a
     new metric.
2. **Drop the `worked` column** (old M). Semantics now:
   - `posted_at` non-empty → commented (done);
   - `posted_at` empty + `reject_reason` non-empty → skipped;
   - both empty → not yet worked.
3. **Merge `variant_used` into `posted_text`** (drop `variant_used`).
   `posted_text` convention: operator enters `1`/`2`/`3` = that variant
   taken verbatim; any other non-empty content = hand-written/edited text.
   ⚠️ **Type coercion:** Sheets turns a bare `1` into a NUMBER — gspread may
   return int `1` or float `1.0`. Handle both ends:
   - Prevention: set `numberFormat: TEXT` on the posted_text column in the
     setup script;
   - Tolerant parse (for the future ingestion of edits): normalize
     `str(value).strip()`, strip trailing `.0` on numeric strings, THEN
     compare against {"1","2","3"}. Unit tests: int, float, string, padded
     string, real text inputs.
4. Final operator columns: `posted_text`, `reject_reason`, `posted_at`.
5. **Migrate the live sheet**: insert/remove columns per above WITHOUT
   losing the 60 retro-loaded rows; backfill `post_date` and
   `quality_score` for the existing 07-05 rows from saved run artifacts
   (06-22 rows: backfill if recoverable from saved CSVs, else blank).

## Task 2 — Sheet ergonomics (operator works here nightly now)

In the setup script (idempotent):
- Freeze header row + columns through `rank`.
- `posted_text` column wide (~400px) with text wrap; variant columns
  readable width with wrap.
- Conditional format: rows with empty `posted_at` AND empty `reject_reason`
  AND date < today → light amber (overdue).
- Basic filter enabled on daily_log so recency/rank sorting is one click.
- Update the `nav` tab reference card to the new conventions (posted_at =
  done; posted_text = 1/2/3 or text).

## Task 3 — Full-width regen (30 → 81)

1. Configurable final-sheet cutoff: `top_n` in config/client YAML, CLI
   `--top-n`, value `all`/0 = every gate-KEPT post ("avoid" excluded).
   Default stays 30.
2. **⛔ STOP — get go-ahead for the paid call** (~51 additional posts ×
   generation+judging, gpt-4.1-mini — cents).
3. Run `--skip-collect --top-n all` on today's saved run. Reusing the
   existing top-30 outputs is optional; if reuse plumbing exceeds ~30 min,
   regen all 81.
4. Append the new rows to daily_log — **per-action_id dedup** (refine the
   current guard if it is per client+date), so the 51 new rows join
   today's 30 without duplication. All 81 rows must carry `post_date`,
   `quality_score`, and `source_keywords` (same URL-matching backfill that
   worked for the 30).
5. CSV output `comment_sheet_2026-07-05_full.csv` still written (archive
   convention), but the sheet is the delivery.

## Task 4 — Exclusion read (must exist before Thursday's run)

1. `feedback/sheet_client.py::load_exclusions(client, author_cooldown_days=7)`:
   - `commented_post_urls`: post_url where `posted_at` is non-empty;
   - `touched_authors`: stable author identifier (profile URL if available
     in run artifacts, else author_name) where posted_at within cooldown.
2. Apply at collection/filter stage: drop commented URLs (permanent);
   drop cooldown authors with avoid reason `author cooldown (Nd)`.
   Cooldown per-client configurable.
3. Fail-soft: sheet unreachable → warn loudly in run summary, proceed
   without exclusions.
4. Retire any CSV-based feedback ingestion code path if present.
5. Unit tests: set construction from mocked rows incl. int/float
   posted_text cells, cooldown window edges, fail-soft.
6. **Dry test tonight:** after the operator fills posted_at for the first
   batch, run a standalone exclusion print (no pipeline run) and show the
   sets. **⛔ STOP** — operator eyeballs that tonight's posts/authors
   appear correctly. This is the acceptance test Thursday depends on.

## Task 5 — Runner demotion

1. Stop auto-building the comment-runner HTML after runs. Keep
   `planner/comment_runner.py` behind an explicit `--runner` flag (cheap
   to keep, zero maintenance promise). Remove runner references as the
   primary workflow from the runbook; sheet is the cockpit.
2. The runner's "export CSV backup" role is dead — the sheet's own
   fallback CSV (already implemented) covers sheet-outage risk.

## Task 6 — Thursday pre-flight (verify + report, don't change today)

Report current state of:
- `max_post_age_days` — must be 7 before Thursday's collection (was set
  to 14 for the 07-05 run; confirm whether reverted/committed);
- exclusion read wired into the collection stage (Task 4.2);
- one-line reminder in the run summary if any daily_log rows older than
  2 days are unworked.

---

## Operator items (unchanged from session report, not CC work)
1. Rotate the Apify token (old scratch logs captured it in URLs).
2. Verify/fill the 06-22 cost row from the Apify console.
3. Tonight: work the sheet (sort by post_date desc, then quality_score),
   fill posted_text/reject_reason/posted_at; then trigger the Task 4.6
   dry test.
