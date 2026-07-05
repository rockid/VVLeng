"""Unit tests for feedback/sheet_client.py — all gspread calls mocked."""

import os
import csv
from unittest.mock import MagicMock, patch, call
from datetime import date

import pytest

import feedback.sheet_client as sc


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_config(client_id="Joinee", dry_run=False):
    cfg = MagicMock()
    cfg.client_id = client_id
    cfg.dry_run = dry_run
    return cfg


def _make_ws(existing_rows=None):
    """Mock worksheet with configurable existing data rows."""
    ws = MagicMock()
    header = [
        "date","client","action_id","post_url","author_name","author_tier",
        "rank","post_date","quality_score","source_keywords",
        "variant_1","variant_2","variant_3",
        "judge_confidence","posted_text","reject_reason","posted_at",
    ]
    rows = [header] + (existing_rows or [])
    ws.get_all_values.return_value = rows
    return ws


def _sample_dl_rows(run_date="2026-07-05", client="Joinee", n=2):
    return [
        [run_date, client, f"act_{i:03d}", f"https://li.com/{i}",
         f"Author {i}", "tier1", i, "2026-07-01", 0.72, "kw1, kw2",
         f"v1_{i}", f"v2_{i}", f"v3_{i}", "4"]
        for i in range(1, n + 1)
    ]


# ── append_daily_log ─────────────────────────────────────────────────────────

def test_append_daily_log_happy_path(tmp_path, monkeypatch):
    """Rows are padded to 17 cols and appended in one call."""
    ws = _make_ws()
    sh = MagicMock()
    sh.worksheet.return_value = ws
    monkeypatch.setattr(sc, "_get_client", lambda cfg: (MagicMock(), sh))

    rows = _sample_dl_rows()
    sc.append_daily_log(rows, _make_config(), fallback_dir=str(tmp_path))

    ws.append_rows.assert_called_once()
    appended = ws.append_rows.call_args[0][0]
    assert len(appended) == 2
    assert all(len(r) == 17 for r in appended), "rows must be padded to 17 cols"
    assert appended[0][14] == ""   # col O (posted_text) blank — operator fills


def test_append_daily_log_dedup_guard(tmp_path, monkeypatch):
    """If rows for (date, client) already exist, append is skipped."""
    existing = [["2026-07-05", "Joinee"] + ["x"] * 15]
    ws = _make_ws(existing_rows=existing)
    sh = MagicMock()
    sh.worksheet.return_value = ws
    monkeypatch.setattr(sc, "_get_client", lambda cfg: (MagicMock(), sh))

    sc.append_daily_log(_sample_dl_rows(), _make_config(), fallback_dir=str(tmp_path))

    ws.append_rows.assert_not_called()


def test_append_daily_log_fallback_on_sheet_error(tmp_path, monkeypatch):
    """On sheet error, a fallback CSV is written and no exception raised."""
    monkeypatch.setattr(sc, "_get_client", lambda cfg: (None, None))

    rows = _sample_dl_rows()
    sc.append_daily_log(rows, _make_config(), fallback_dir=str(tmp_path))

    fallbacks = list(tmp_path.glob("feedback_fallback_*.csv"))
    assert len(fallbacks) == 1
    with open(fallbacks[0], encoding="utf-8") as f:
        content = f.read()
    assert "act_001" in content


def test_append_daily_log_empty_rows_is_noop(monkeypatch):
    """Empty rows list returns immediately without touching the sheet."""
    called = []
    monkeypatch.setattr(sc, "_get_client", lambda cfg: called.append(1) or (None, None))
    sc.append_daily_log([], _make_config())
    assert not called


# ── append_run_cost ──────────────────────────────────────────────────────────

def test_append_run_cost_happy_path(monkeypatch):
    rc_ws = MagicMock()
    rc_ws.get_all_values.return_value = [
        ["run_date","client","posts_collected","max_posts_per_kw",
         "n_keywords","apify_cost_usd","llm_cost_note"]
    ]
    sh = MagicMock()
    sh.worksheet.return_value = rc_ws
    monkeypatch.setattr(sc, "_get_client", lambda cfg: (MagicMock(), sh))

    row = ["2026-07-05","Joinee","1624","35","48","","gpt-4.1-mini"]
    sc.append_run_cost(row, _make_config())
    rc_ws.append_rows.assert_called_once_with([row], value_input_option="USER_ENTERED")


def test_append_run_cost_dedup_guard(monkeypatch):
    rc_ws = MagicMock()
    rc_ws.get_all_values.return_value = [
        ["run_date","client"],
        ["2026-07-05","Joinee"],
    ]
    sh = MagicMock()
    sh.worksheet.return_value = rc_ws
    monkeypatch.setattr(sc, "_get_client", lambda cfg: (MagicMock(), sh))

    sc.append_run_cost(["2026-07-05","Joinee","1624","35","48","",""], _make_config())
    rc_ws.append_rows.assert_not_called()


# ── end-of-run checklist ─────────────────────────────────────────────────────

def test_checklist_flags_unworked_rows(monkeypatch, capsys):
    yesterday = (date.today() - __import__("datetime").timedelta(days=1)).isoformat()
    dl_header = ["date","client","action_id","post_url","author_name","author_tier",
                 "rank","post_date","quality_score","source_keywords",
                 "variant_1","variant_2","variant_3",
                 "judge_confidence","posted_text","reject_reason","posted_at"]
    dl_rows = [[yesterday,"Joinee","act_001","http://x","A","tier1",
                "1","2026-06-30","0.72","kw","v1","v2","v3","4","","",""]]   # posted_at = blank

    eng_header = ["posted_date","post_url","likes_on_our_comment","replies_on_our_comment",
                  "replier_profile_urls","author_replied","checked_at","notes"]
    wk_header = ["week_start","profile_views","search_appearances",
                 "incoming_connection_requests","notes"]
    wk_rows = [date.today().isoformat()]  # fresh weekly entry

    def _ws(title):
        ws = MagicMock()
        if title == sc._DAILY_LOG_TAB:
            ws.get_all_values.return_value = [dl_header] + dl_rows
        elif title == sc._ENGAGEMENT_TAB:
            ws.get_all_values.return_value = [eng_header]
        elif title == sc._WEEKLY_TAB:
            ws.get_all_values.return_value = [wk_header, wk_rows]
        return ws

    sh = MagicMock()
    sh.worksheet.side_effect = _ws
    monkeypatch.setattr(sc, "_get_client", lambda cfg: (MagicMock(), sh))

    sc.print_end_of_run_checklist(_make_config())
    out = capsys.readouterr().out
    assert "unworked" in out


def test_checklist_silent_when_sheet_unavailable(monkeypatch, capsys):
    """No output and no exception when sheet is unreachable."""
    monkeypatch.setattr(sc, "_get_client", lambda cfg: (None, None))
    sc.print_end_of_run_checklist(_make_config())
    assert capsys.readouterr().out == ""


# ── Phase 3: matched_keywords accumulation ───────────────────────────────────

def test_matched_keywords_accumulated_across_duplicates():
    """Dedup survivor carries all source_query values from duplicate copies."""
    from run_pipeline import apply_content_filters

    cfg = MagicMock()
    cfg.defaults.max_post_age_days = 365
    cfg.client.collection.min_engagement_tier1 = 0
    cfg.client.collection.min_engagement_tier2 = 0

    shared_text = "A" * 100   # same prefix
    posts = [
        {"id":"1","text":shared_text,"posted_at":None,"likes_count":10,
         "comments_count":0,"keyword_tier":"tier1","source_query":"community ops"},
        {"id":"2","text":shared_text,"posted_at":None,"likes_count":10,
         "comments_count":0,"keyword_tier":"tier1","source_query":"community management"},
    ]
    kept, stats = apply_content_filters(posts, cfg)
    assert len(kept) == 1
    assert stats["removed_duplicate_text"] == 1
    kws = kept[0].get("matched_keywords", [])
    assert "community ops" in kws
    assert "community management" in kws


def test_unique_posts_get_single_keyword():
    """Posts with unique text get a single-element matched_keywords list."""
    from run_pipeline import apply_content_filters

    cfg = MagicMock()
    cfg.defaults.max_post_age_days = 365
    cfg.client.collection.min_engagement_tier1 = 0
    cfg.client.collection.min_engagement_tier2 = 0

    posts = [
        {"id":"1","text":"unique post alpha " * 5,"posted_at":None,
         "likes_count":5,"comments_count":0,"keyword_tier":"tier1",
         "source_query":"alumni engagement"},
        {"id":"2","text":"unique post beta " * 5,"posted_at":None,
         "likes_count":5,"comments_count":0,"keyword_tier":"tier1",
         "source_query":"community building"},
    ]
    kept, _ = apply_content_filters(posts, cfg)
    assert len(kept) == 2
    assert kept[0]["matched_keywords"] == ["alumni engagement"]
    assert kept[1]["matched_keywords"] == ["community building"]


# ── load_exclusions ───────────────────────────────────────────────────────────

def _make_dl_ws_for_exclusions(rows):
    ws = MagicMock()
    header = ["date","client","action_id","post_url","author_name","author_tier",
              "rank","post_date","quality_score","source_keywords",
              "variant_1","variant_2","variant_3","judge_confidence",
              "posted_text","reject_reason","posted_at"]
    ws.get_all_values.return_value = [header] + rows
    return ws


def test_load_exclusions_commented_url(monkeypatch):
    """Posted URLs appear in commented_post_urls."""
    today = date.today().isoformat()
    rows = [
        ["2026-07-05","Joinee","act_001","https://li.com/p1","Alice","tier1",
         "1","2026-07-01","0.72","kw","v1","v2","v3","4","1","",""],        # no posted_at
        ["2026-07-05","Joinee","act_002","https://li.com/p2","Bob","tier1",
         "2","2026-07-01","0.68","kw","v1","v2","v3","4","1","",today],     # posted
    ]
    ws = _make_dl_ws_for_exclusions(rows)
    sh = MagicMock()
    sh.worksheet.return_value = ws
    monkeypatch.setattr(sc, "_get_client", lambda cfg: (MagicMock(), sh))

    excl = sc.load_exclusions("Joinee", _make_config())
    assert "https://li.com/p2" in excl["commented_post_urls"]
    assert "https://li.com/p1" not in excl["commented_post_urls"]


def test_load_exclusions_author_cooldown(monkeypatch):
    """Author with recent posted_at appears in touched_authors within cooldown."""
    today = date.today().isoformat()
    old_date = "2020-01-01"
    rows = [
        ["2026-07-05","Joinee","act_001","https://li.com/p1","Alice","tier1",
         "1","2026-07-01","0.72","kw","v1","v2","v3","4","1","",today],    # recent — in cooldown
        ["2026-07-05","Joinee","act_002","https://li.com/p2","Bob","tier1",
         "2","2026-07-01","0.68","kw","v1","v2","v3","4","1","",old_date],  # old — not in cooldown
    ]
    ws = _make_dl_ws_for_exclusions(rows)
    sh = MagicMock()
    sh.worksheet.return_value = ws
    monkeypatch.setattr(sc, "_get_client", lambda cfg: (MagicMock(), sh))

    excl = sc.load_exclusions("Joinee", _make_config(), author_cooldown_days=7)
    assert "Alice" in excl["touched_authors"]
    assert "Bob" not in excl["touched_authors"]


def test_load_exclusions_fail_soft(monkeypatch):
    """Returns empty sets when sheet is unreachable — never raises."""
    monkeypatch.setattr(sc, "_get_client", lambda cfg: (None, None))
    excl = sc.load_exclusions("Joinee", _make_config())
    assert excl == {"commented_post_urls": set(), "touched_authors": set()}


def test_load_exclusions_ignores_other_clients(monkeypatch):
    """Rows for a different client are not included in exclusions."""
    today = date.today().isoformat()
    rows = [
        ["2026-07-05","OtherClient","act_001","https://li.com/p1","Alice","tier1",
         "1","2026-07-01","0.72","kw","v1","v2","v3","4","1","",today],
    ]
    ws = _make_dl_ws_for_exclusions(rows)
    sh = MagicMock()
    sh.worksheet.return_value = ws
    monkeypatch.setattr(sc, "_get_client", lambda cfg: (MagicMock(), sh))

    excl = sc.load_exclusions("Joinee", _make_config())
    assert len(excl["commented_post_urls"]) == 0
    assert len(excl["touched_authors"]) == 0


# ── posted_text coercion (variant indicator 1/2/3) ───────────────────────────

def test_posted_text_coercion():
    """Normalize posted_text: int, float, padded string, real text, all handled."""
    def _normalize(val):
        s = str(val).strip()
        if s.endswith(".0") and s[:-2].isdigit():
            s = s[:-2]
        return s

    assert _normalize(1) == "1"
    assert _normalize(1.0) == "1"
    assert _normalize("1") == "1"
    assert _normalize("  2 ") == "2"
    assert _normalize("Great observation!") == "Great observation!"
    assert _normalize(3.0) == "3"
