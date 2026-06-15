# LinkedIn Intelligence System — Session Handoff Summary
Date: 2026-06-14 (updated end-of-day)
Next session should start by reading this document AND the previous handoff (2026-06-13).

---

## 1. Current Build Status

### Phase 0 — COMPLETE
- Dry run passes cleanly
- DB initializes correctly
- Normaliser verified against confirmed Apify field mapping
- Real Apify collector call works (harvestapi~linkedin-post-search)
- LLM connectivity confirmed working

### Phase 1 — COMPLETE (all tests passed this session)
- Step 0: Existing unit tests pass
- Step 1: Dry run ✅
- Step 2: DB initialization ✅ — `data/joinee/engagement.db` created with all tables
- Step 3: Normaliser verified against confirmed field mapping ✅
- Step 4: Real Apify collector call ✅ (~$0.05)
- Step 5: LLM connectivity ✅
- All module tests passing

### Phase 2 — NOT STARTED
Original modules:
- `processor/semantic_filter.py`
- `processor/post_scorer.py`
- `content/signal_extractor.py`
- `collector/route_keywords.py` (partial)

People pipeline modules (new — see architecture amendment):
- `processor/icp_checker.py`
- `processor/profile_scraper.py`
- `processor/touch_recorder.py`
- `processor/delayed_scrape.py`
- `processor/influencer_ranker.py`
- `db/people_schema.py`

---

## 2. Active Client

- Client ID: `joinee`
- Config: `clients/joinee.yaml`
- Data folder: `data/joinee/`
- DB: `data/joinee/engagement.db`
- All docs in: `/docs` folder

---

## 3. Tech Stack Decisions (final)

### LLM Models (via laozhang.ai)
```yaml
llm:
  default_model: "gemini-2.5-flash-lite"   # ⚠️ UPDATED — was gpt-4o-mini. Verify on LZ before committing.
  comment_model: "gpt-4.1-mini"
  hook_model: "gpt-4.1-mini"
  signal_model: "gpt-4.1-mini"
  scoring_model: "gpt-4.1-mini"
```
- LZ base URL: `https://api.laozhang.ai/v1`
- `LLM_BASE_URL` and `LLM_API_KEY` in `.env`
- Models in `config.yaml` (NOT in `.env`)

### Apify Actors
| Actor | Config key | Status |
|---|---|---|
| `harvestapi~linkedin-post-search` | `post_search` | ✅ Validated & working |
| `harvestapi~linkedin-profile-posts` | `profile_scraper` | ✅ Validated this session |
| `follower_scraper` | — | 🔒 Locked — Phase 5 only |

**Critical:** Apify actor IDs in API calls must use `~` not `/` — e.g. `harvestapi~linkedin-post-search`. The `/` causes 404.

### Route 1 Field Mapping (harvestapi~linkedin-profile-posts, confirmed)
```json
{
  "post_id":         "item.id",
  "url":             "item.linkedinUrl",
  "content":         "item.content",
  "author_id":       "item.author.id",
  "author_name":     "item.author.name",
  "author_handle":   "item.author.publicIdentifier",
  "author_url":      "item.author.linkedinUrl",
  "author_headline": "item.author.info",
  "posted_at":       "item.postedAt.date",
  "timestamp_ms":    "item.postedAt.timestamp",
  "likes":           "item.engagement.likes",
  "comments":        "item.engagement.comments",
  "shares":          "item.engagement.shares",
  "has_images":      "item.postImages.length > 0",
  "source_query":    "item.query.targetUrl"
}
```
**Differences from Route 2:** only `source_query` differs (`item.query.targetUrl` vs `item.query.search`). Everything else identical.

**Critical:** Actor output includes `type: "reaction"` and `type: "comment"` items mixed in with `type: "post"`. Normaliser must filter `item.type === "post"` before processing.

### Route 2 Field Mapping (harvestapi~linkedin-post-search, confirmed, unchanged)
```json
{
  "post_id":         "item.id",
  "url":             "item.linkedinUrl",
  "content":         "item.content",
  "author_id":       "item.author.id",
  "author_name":     "item.author.name",
  "author_handle":   "item.author.publicIdentifier",
  "author_url":      "item.author.linkedinUrl",
  "author_headline": "item.author.info",
  "posted_at":       "item.postedAt.date",
  "timestamp_ms":    "item.postedAt.timestamp",
  "likes":           "item.engagement.likes",
  "comments":        "item.engagement.comments",
  "shares":          "item.engagement.shares",
  "has_images":      "item.postImages.length > 0",
  "source_query":    "item.query.search"
}
```
Warnings:
- `author.universalName` is null — use `author.publicIdentifier`
- `engagement` is nested — `item.engagement.likes` not `item.likes`
- Use `item.postedAt.date` (ISO string) for DB, not timestamp

---

## 4. Bugs Fixed This Session

| Bug | Fix |
|---|---|
| Apify 404 on actor call | Actor ID needs `~` not `/` in API URL |
| LLM connection error `Bearer ` | `LLM_DEFAULT_MODEL` was missing from `.env` — moved models to config.yaml, added `default_model` field |
| `llm_client.py` using `comment_model` as default | Fixed fallback chain: `default_model` → env var → hardcoded fallback. `comment_model` is task-specific, not a default |
| DB path hardcoded to `data/engagement.db` | Fixed to be client-aware: `data/{client_id}/engagement.db` |

---

## 5. Architecture Decisions Made This Session

All decisions below are documented in full in `docs/architecture_amendment_phase2_people.md`.

### Relationship State Machine
States: `discovered → icp_rejected | icp_candidate → icp_confirmed | influencer → warming → contacted → connected | withdrawn → (cooldown) → icp_confirmed`

### Touch Scoring
| Touch | Multiplier |
|---|---|
| Comment (either direction) | 1.0 |
| Their like on operator's post | 0.7 |
| Operator like on their post | 0.5 |
| Ambient (same post, different actor) | 0.1 |

Starting threshold: 2.0 (configurable). Becomes part of candidate ranking formula later.

### Delayed Scrape
- Top 10 posts/day selected by `engagement_total × influencer.icp_pct`
- Scraped 3 days after shortlisting (operator has acted manually by then)
- `scrapeComments: true`, `scrapeReactions: true`, max 50 each
- Auto-detects operator's touches by matching `operator_linkedin_id` in scrape output

### Profile Scrape Batching
- Once/day at collection time
- Rank `icp_candidates` by touch score + recency
- Scrape top N (configurable `profile_scrape.daily_cap`, start 50)
- Stop when desired quantity + margin reached

### Influencer Flag & Ranking
- Threshold: 1+ post/week AND (30+ avg likes OR 15+ avg comments) — harden later
- Ranking formula: `posts_per_week × avg_engagement × icp_pct`
- Auto-add to watchlist after 2 operator comment selections
- Warming = direct engagement only (ambient touches not counted for influencers)

### ICP Graph
Many-to-many table `icp_influencer_graph`: ICP-confirmed persons → all influencers whose posts they appeared in. Tracks `appearance_count` and `last_seen_at`. ICPs only.

### Repost cap
Max 2 reposts/week. Max ~5 total posts/week (reposts must earn their place).

### Semantic filter threshold
Start at 0.35 for tier1. Tune after first real run — no fixed decision yet.

### People collection
3 sources: post authors (free, every post), delayed scrape participants (paid, top N posts), manual adds.

### Influencer discovery
KW search + delayed scrape loop expected to surface influencers organically. "Who do ICPs follow" follower graph approach parked — Phase 5.

---

## 6. Config Changes Required Before Phase 2

### `config.yaml` — add:
```yaml
relationship:
  touch_threshold: 2.0
  contact_timeout_days: 21
  cooldown_days: 28

influencer:
  min_posts_per_week: 1
  min_avg_likes: 30
  min_avg_comments: 15
  watchlist_auto_add_comment_count: 2

delayed_scrape:
  lag_days: 3
  posts_per_day: 10
  max_comments_per_post: 50
  max_reactions_per_post: 50

profile_scrape:
  daily_cap: 50

llm:
  default_model: "gemini-2.5-flash-lite"   # verify on LZ first
```

### `clients/joinee.yaml` — add:
```yaml
operator_linkedin_id: "YOUR_HANDLE_HERE"
influencer_watchlist:   # seed with 3 confirmed profiles
  - "https://www.linkedin.com/in/profile1/"
  - "https://www.linkedin.com/in/profile2/"
  - "https://www.linkedin.com/in/profile3/"
```

---

## 7. Files Produced This Session (in /docs)

| File | Purpose |
|---|---|
| `CLINE.md` | Cline working rules — loaded automatically at session start |
| `architecture_backlog.md` | Parking lot for future features — read-only for Cline |
| `cline_testing_instructions.md` | Step-by-step test instructions for Cline |
| `pre_launch_test_plan_v2.md` | Human operator test plan (updated from v1) |
| `session_handoff_2026-06-14.md` | This document |
| `architecture_amendment_phase2_people.md` | Full people pipeline spec — hand to Cline for Phase 2 |

---

## 8. Cline Working Notes

- **Model:** DeepSeek-V4-Flash via LZ works fine for this project — do not switch unless hanging recurs
- **Session style:** Short focused sessions work better than long ones. New Task between sessions, not Resume.
- **progress.md:** Must be updated after every step, debug cycle, and before session end. See CLINE.md Section 8.
- **Plan mode first:** Always start new Cline session in Plan mode to get step inventory before Act mode
- **CLINE.md location:** Project root — Cline reads it automatically if set as custom instructions file

---

## 9. Open Decisions (carry forward)

1. **Semantic filter threshold** — 0.35 is starting value, tune after first real run. No hard decision yet.
2. **`gemini-2.5-flash-lite` on LZ** — verify model string available before Cline commits it to config. If unavailable, fall back to `gpt-4o-mini` and note in progress.md.
3. **Touch threshold tuning** — starts at 2.0, will become part of candidate ranking formula in later phase.
4. **Influencer thresholds** — 1 post/week, 30 likes, 15 comments are soft starts. Harden once volume established.

---

## 10. Immediate Next Actions

1. **Add `operator_linkedin_id`** to `clients/joinee.yaml` (your LinkedIn handle)
2. **Seed influencer watchlist** with your 3 known profile URLs in `clients/joinee.yaml`
3. **Verify `gemini-2.5-flash-lite`** is available on laozhang.ai, then update `config.yaml`
4. **Start Phase 2 with Cline** — hand:
   - `CLINE.md`
   - `docs/architecture_amendment_phase2_people.md`
   - Tell Cline: *"All Phase 0 and Phase 1 tests passing. Start Phase 2. Read progress.md and architecture_amendment_phase2_people.md first. Build in the order specified in the amendment Section 13."*

---

## 11. Backlog Highlights (not for current build)

- Influencer discovery via follower graph ("who do ICPs follow") — Phase 5
- Comment content scraping for signal extraction — Phase 4-5
- G2/Capterra reviews as signal source — highest value next after LinkedIn pipeline stable
- Route 3 follow graph traversal — Phase 5, 2+ weeks stable running first
- Reddit listener — parked, wrong channel for this niche
- Multi-client expansion — after Joinee pipeline validated
- Personalized connection message drafting — after `connected` state, manual for now

Full backlog: `docs/architecture_backlog.md`
