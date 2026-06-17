# Architecture Amendment — Collector Upgrade + People Pipeline & Relationship Engine
Date: 2026-06-14 (collector section added 2026-06-15)
Status: APPROVED — implement Phase 1.5 first, then Phase 2

This document extends the original architecture with:
- **Phase 1.5** (do first): collector upgrade — relevance sort, waterfall logic, KW rotation, dynamic threshold
- **Phase 2**: people pipeline, relationship state machine, influencer ranking, delayed scrape

Hand to Cline alongside CLINE.md. Build Phase 1.5 before starting Phase 2.

---

## Overview

The system has two parallel pipelines:
1. **Post pipeline** (original) — collect posts, score, generate comment/repost actions
2. **People pipeline** (this amendment) — discover people, qualify as ICP, warm up, feed outreach

The people pipeline is the bridge between content intelligence and LinkedIn outreach. Its output is a daily ranked shortlist of ICP candidates ready for connection requests.

---

## PHASE 1.5 — Collector Upgrade (build before Phase 2)

### Background

Empirical testing (2026-06-15) showed that `sortBy: relevance` dramatically outperforms `sortBy: date` for post quality:
- 15+ engagement posts: 7% (date) vs 35% (relevance)
- Top post engagement: 137 (date) vs 795 (relevance)

Testing also showed 553 unique posts across 20 tier-1 KWs at 30 posts each yielded 16 posts with 200+ total engagement — more than enough to produce the weekly shortlist of 15. This enables a waterfall approach that stops fetching as soon as the target is met, minimising cost.

---

### 1.5.1 Sort Order Change

**One-line fix. Do this first.**

In the collector, change all KW search calls from `sortBy: date` to `sortBy: relevance`. Apply to all tiers. Route 1 (influencer profile posts) is unaffected — it uses a different actor.

---

### 1.5.2 Waterfall Collection Logic

Replace the current batch-all-keywords approach with a sequential waterfall that stops when the target is met.

**Algorithm:**
```
target_candidates = waterfall.target_candidates        # config, default 40
always_run = waterfall.always_run_top_n               # config, default 3
explore_slots = waterfall.explore_slots               # config, default 2

# Build run order for this execution
run_order = top N KWs by yield_score (from kw_stats table)
            + explore_slots random picks from remaining KWs (all tiers)

candidates = []

for kw in run_order:
    if len(candidates) >= target_candidates:
        break
    posts = apify_fetch(kw, maxPosts=waterfall.fetch_per_kw, sortBy=relevance)
    update_kw_stats(kw, posts)           # record total fetched, eng_sum
    candidates += posts                  # dedup handled after loop

# After waterfall completes:
candidates = dedupe(candidates)
candidates = filter(candidates, min_length, max_age, blocked_substrings)
# Dynamic threshold: sort by engagement desc, take top target_shortlist
candidates_sorted = sort(candidates, by=engagement desc)
shortlist = candidates_sorted[:waterfall.target_shortlist]   # default 15
record_cutoff_engagement(shortlist[-1].engagement)           # for monitoring
```

**Key points:**
- Waterfall stops early on good weeks — cheap runs
- Always-run slots ensure top KWs are refreshed every time
- Explore slots ensure bottom KWs get sampled periodically — stats stay fresh
- All tiers (1, 2, 3) are in the same pool, ranked by historical yield. Tier 2/3 KWs naturally get called when tier 1 KWs are exhausted or in explore slots.
- Dynamic threshold: no fixed engagement floor — always returns exactly `target_shortlist` posts, self-adjusting to weekly supply

---

### 1.5.3 KW Stats Table

New DB table to track per-keyword yield history.

```sql
CREATE TABLE kw_stats (
    keyword         TEXT PRIMARY KEY,
    tier            INTEGER,            -- 1, 2, or 3
    total_runs      INTEGER DEFAULT 0,
    total_fetched   INTEGER DEFAULT 0,
    total_eng_sum   INTEGER DEFAULT 0,
    avg_eng_per_post REAL DEFAULT 0.0,  -- updated after each run
    yield_score     REAL DEFAULT 5.0,   -- starts neutral; updated after each run
    last_run_at     TEXT,
    last_fetched    INTEGER DEFAULT 0,  -- posts fetched in last run
    last_eng_sum    INTEGER DEFAULT 0   -- engagement sum in last run
);
```

**Yield score formula** (updated after each run for this KW):
```
yield_score = avg_eng_per_post
```
Simple and interpretable. KWs with higher average engagement per post rank higher. New KWs start at 5.0 (neutral — gets explored before being ranked down).

**Initialisation:** Populate from today's analysis results as starting values:

| Keyword | Tier | Initial yield_score |
|---|---|---|
| online community platform | 1 | 58.9 |
| member engagement platform | 1 | 55.8 |
| community management platform | 1 | 65.2 |
| community building software | 1 | 49.5 |
| community operations | 1 | 45.7 |
| alumni community platform | 1 | 42.2 |
| community activation | 1 | 39.8 |
| accelerator community management | 1 | 34.6 |
| community retention | 1 | 32.6 |
| network engagement platform | 1 | 29.0 |
| community engagement software | 1 | 25.1 |
| community-led growth | 1 | 21.4 |
| community health metrics | 1 | 22.0 |
| peer learning community | 1 | 19.1 |
| customer community platform | 1 | 14.6 |
| branded community platform | 1 | 9.1 |
| cohort community management | 1 | 9.3 |
| community flywheel | 1 | 8.6 |
| member activation software | 1 | 6.8 |
| community monetization | 1 | 5.7 |
| *(all tier 2 and tier 3 KWs)* | 2/3 | 5.0 |

---

### 1.5.4 Config Keys (add to `config.yaml` under `waterfall:`)

```yaml
waterfall:
  target_candidates: 40       # stop waterfall when this many posts collected (before dedup/filter)
  target_shortlist: 15        # final posts returned after dynamic threshold
  fetch_per_kw: 30            # maxPosts per keyword call
  always_run_top_n: 3         # always run these top KWs by yield_score
  explore_slots: 2            # random picks from non-top KWs per run
```

---

### 1.5.5 New Module: `collector/waterfall.py`

Responsibilities:
- Load KW list + yield scores from `kw_stats` table
- Build run order (top N + random explore slots)
- Execute waterfall loop — call Apify per KW, stop when target met
- Update `kw_stats` after each KW completes
- Return deduplicated, filtered, dynamically-thresholded shortlist
- Log cutoff engagement score for monitoring

Replaces the current batch collection logic in `collector/route_keywords.py`. The existing module can be refactored or wrapped — do not delete, just redirect calls through waterfall.

---

### 1.5.6 Cline Build Order for Phase 1.5

**Step 1.5.0 — Sort order fix**
Change `sortBy` to `relevance` in all KW actor calls. Test with dry run. Verify in logs.

**Step 1.5.1 — KW stats DB table**
Add `kw_stats` table to DB schema. Populate initial yield scores from the table in Section 1.5.3. Verify table created and seeded.

**Step 1.5.2 — Waterfall module**
Build `collector/waterfall.py`. Unit test with mocked Apify calls (dry run). Verify: stops at target, updates kw_stats, returns correct shortlist size.

**Step 1.5.3 — Wire waterfall into pipeline**
Replace batch KW collection call in orchestrator with waterfall call. Full dry run. Then one live run with real Apify calls — verify cost is within budget, shortlist looks sensible.

**Step 1.5.4 — Verify and document**
Check `kw_stats` table is updating correctly after live run. Update `progress.md`. Confirm Phase 1.5 complete before starting Phase 2.

---

## PHASE 2 — People Pipeline & Relationship Engine

### Overview

---

## 1. Relationship State Machine

Every person discovered by the system gets a profile record with a state. States are linear with one branch for rejection.

```
discovered
    ├── icp_rejected        (terminal — headline LLM check = negative)
    └── icp_candidate
            └── icp_confirmed
                    ├── [influencer flag = true/false, set separately]
                    └── warming (score accumulates)
                            └── contacted (connection request sent)
                                    ├── connected (accepted)
                                    └── withdrawn (not accepted in N weeks)
                                            └── back to icp_confirmed after cooldown
```

### State Transition Rules

| From | To | Trigger |
|---|---|---|
| `discovered` | `icp_rejected` | Headline LLM check = negative |
| `discovered` | `icp_candidate` | Headline LLM check = not negative |
| `icp_candidate` | `icp_confirmed` | Profile scraped + LLM ICP check = positive |
| `icp_candidate` | `icp_rejected` | Profile scraped + LLM ICP check = negative |
| `icp_confirmed` | `warming` | First touch recorded |
| `warming` | `contacted` | Operator sends connection request (manual, recorded in system) |
| `contacted` | `connected` | Operator records acceptance |
| `contacted` | `withdrawn` | `contact_sent_at` + 21 days elapsed, no acceptance |
| `withdrawn` | `icp_confirmed` | `withdrawn_at` + 28 days elapsed (cooldown) |

All timing thresholds in `config.yaml` under `relationship:`.

---

## 2. Touch Scoring

Touches are interactions between the operator and a person (or ambient co-presence). Each touch adds to the person's `warming_score`.

### Touch Types & Multipliers

| Touch type | Multiplier | Notes |
|---|---|---|
| `comment_theirs` | 1.0 | Operator commented on their post |
| `comment_mine` | 1.0 | They commented on operator's post |
| `like_theirs` | 0.7 | They liked operator's post |
| `like_mine` | 0.5 | Operator liked their post |
| `ambient` | 0.1 | Both present in same post (different commenter/liker) |

`warming_score = sum(touch.multiplier for all touches)`

### Config keys (under `relationship:`)
```yaml
relationship:
  touch_threshold: 2.0          # warming_score to flag as ready for contact
  contact_timeout_days: 21      # days before withdrawal
  cooldown_days: 28             # days before re-entry after withdrawal
  ambient_min_for_display: 10   # ambient touches needed before shown in UI (not used in score calc)
```

### Touch recording
- **Inbound touches** (they engaged with operator's posts) — auto-detected via delayed scrape
- **Outbound touches** (operator engaged with their posts) — auto-detected via delayed scrape (operator's handle present in comments/likes)
- **Ambient touches** — auto-detected via delayed scrape (both present in same post)

Operator's LinkedIn profile ID/handle must be in `clients/joinee.yaml` as `operator_linkedin_id` for auto-detection.

---

## 3. Profile Scrape Batching

### Headline check (cheap, LLM only)
- Run on all newly discovered people daily
- LLM prompt: given headline, is this person plausibly [ICP definition]? Answer: yes / no / unclear
- `no` → `icp_rejected`. `yes` or `unclear` → `icp_candidate`

### Profile scrape (paid, Apify)
- Run once per day at collection time
- Rank `icp_candidates` by: `touch_score DESC, last_seen DESC`
- Scrape top N until desired quantity + margin reached (N in config as `profile_scrape_daily_cap`)
- Remainder stays `icp_candidate`, re-ranked next day
- After scrape: run LLM ICP check on full profile → transition to `icp_confirmed` or `icp_rejected`

---

## 4. Delayed Scrape (People Collection from Shortlisted Posts)

### Why delayed
Operator acts on post shortlist (comments/likes) manually via LinkedIn UI. System cannot observe these actions in real time. Scrape 3 days later to capture the full engagement picture including operator's actions.

### What gets scraped
- The top N shortlisted posts by expected ICP yield (see Section 5)
- `scrapeComments: true`, `scrapeReactions: true`
- `maxComments: 50`, `maxReactions: 50` (adjust in config)
- Filter `item.type === "post"` — discard reaction/comment type items

### What the scrape produces
1. All commenters + likers → `discovered` (if not already in DB)
2. Operator's comment/like detected → outbound touch recorded automatically
3. Their comment/like on operator's post detected → inbound touch recorded
4. Ambient touches: person present in same post as operator → ambient touch recorded

### Config keys (under `delayed_scrape:`)
```yaml
delayed_scrape:
  lag_days: 3
  posts_per_day: 10             # top N posts to scrape
  max_comments_per_post: 50
  max_reactions_per_post: 50
```

---

## 5. Post Selection for Delayed Scrape

Not all shortlisted posts are equal for people collection. Select the top N by expected ICP yield:

`expected_icp = post.engagement_total × influencer.icp_pct`

Where:
- `post.engagement_total` = likes + comments at collection time
- `influencer.icp_pct` = rolling %ICP in that influencer's audience (0–1.0)
- For posts not from a tracked influencer: use global average `icp_pct` as fallback

Posts are ranked by this score, top `delayed_scrape.posts_per_day` selected.

---

## 6. Influencer Records & Ranking

### Influencer flag
A person becomes an influencer when:
- State is `icp_confirmed` AND
- `posts_per_week >= influencer_min_posts_per_week` (config, default 1) AND
- `avg_likes >= influencer_min_avg_likes` OR `avg_comments >= influencer_min_avg_comments` (config, defaults 30 / 15)

Thresholds will be hardened later when volume is established.

### Influencer ranking formula
```
influencer_score = posts_per_week × avg_engagement × icp_pct
```
Where `avg_engagement = avg_likes + avg_comments` and `icp_pct` is the rolling %ICP of their audience.

### Auto-add to watchlist
If an influencer-flagged person has been selected for operator comment 2+ times → auto-add to `clients/joinee.yaml` watchlist (append, do not overwrite).

### Warming strategy for influencers
Direct engagement only (comment on their posts, like their posts). Ambient touches do not count toward influencer warming score — they are still recorded but not used in influencer-specific decisions.

---

## 7. ICP Graph (Person → Influencer Edges)

For every ICP-confirmed person, store all influencers whose posts they were discovered in. This is a many-to-many relationship.

### DB table: `icp_influencer_graph`
```sql
CREATE TABLE icp_influencer_graph (
    person_id       TEXT NOT NULL,      -- profile.author_id
    influencer_id   TEXT NOT NULL,      -- profile.author_id of influencer
    first_seen_at   TEXT NOT NULL,      -- ISO timestamp
    last_seen_at    TEXT NOT NULL,      -- ISO timestamp
    appearance_count INTEGER DEFAULT 1, -- times seen in this influencer's posts
    PRIMARY KEY (person_id, influencer_id)
);
```

Update `last_seen_at` and increment `appearance_count` on each subsequent sighting. ICPs only — do not populate for `icp_candidate` or `icp_rejected` profiles.

---

## 8. %ICP Metric

After each delayed scrape batch:
- Count total profiles discovered from that influencer's posts: `total_seen`
- Count how many passed ICP check (confirmed or candidate-not-yet-checked): `icp_count`
- `icp_pct = icp_count / total_seen` (rolling average, weight recent scrapes higher)

Store on influencer record. Used in ranking formula and post selection scoring.

---

## 9. New Modules Required

| Module | Purpose |
|---|---|
| `processor/icp_checker.py` | Headline LLM check + full profile LLM ICP check |
| `processor/profile_scraper.py` | Batched Apify profile scrape, ranked by touch score |
| `processor/touch_recorder.py` | Parse delayed scrape output, record all touch types |
| `processor/delayed_scrape.py` | Orchestrate delayed scrape: select posts, call Apify, feed touch_recorder |
| `processor/influencer_ranker.py` | Score influencers, update icp_pct, auto-add to watchlist |
| `db/people_schema.py` | New DB tables: profiles, touches, icp_influencer_graph |

---

## 10. New DB Tables

### `profiles`
```sql
CREATE TABLE profiles (
    id                  TEXT PRIMARY KEY,   -- LinkedIn author_id
    handle              TEXT,
    name                TEXT,
    headline            TEXT,
    linkedin_url        TEXT,
    state               TEXT DEFAULT 'discovered',
    icp_confirmed       INTEGER DEFAULT 0,
    influencer          INTEGER DEFAULT 0,
    warming_score       REAL DEFAULT 0.0,
    icp_pct             REAL,               -- for influencers only
    posts_per_week      REAL,               -- for influencers only
    avg_likes           REAL,               -- for influencers only
    avg_comments        REAL,               -- for influencers only
    contact_sent_at     TEXT,
    connected_at        TEXT,
    withdrawn_at        TEXT,
    first_seen_at       TEXT,
    last_seen_at        TEXT,
    source_influencer_id TEXT               -- primary discovery source (first seen)
);
```

### `touches`
```sql
CREATE TABLE touches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id   TEXT NOT NULL,
    touch_type  TEXT NOT NULL,  -- comment_theirs | comment_mine | like_theirs | like_mine | ambient
    multiplier  REAL NOT NULL,
    post_id     TEXT,
    recorded_at TEXT NOT NULL
);
```

### `icp_influencer_graph` — see Section 7.

---

## 11. Config Keys Summary (add to `config.yaml`)

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
  daily_cap: 50     # max profile scrapes per day — tune for cost control
```

Add to `clients/joinee.yaml`:
```yaml
operator_linkedin_id: "YOUR_HANDLE_HERE"
```

---

## 12. LLM Model Update

Swap `default_model` in `config.yaml` immediately — do not wait for Phase 2 stable:
```yaml
llm:
  default_model: "gemini-2.5-flash-lite"   # was gpt-4o-mini
```
Verify model string is available on LZ before committing. If unavailable, fall back to `gpt-4o-mini` and note in progress.md.

---

## 13. Cline Build Order (Phase 2)

**Prerequisite: Phase 1.5 must be complete and verified before starting any step below.**

Work through these steps in order. Update `progress.md` after each. Run tests before moving to next step.

**Step 1 — DB schema**
Create `db/people_schema.py`. Add `profiles`, `touches`, `icp_influencer_graph` tables. Run migration, verify tables created. Do not touch existing tables.

**Step 2 — ICP checker (headline only)**
Build `processor/icp_checker.py`. Implement `check_headline(headline, client_config) → yes/no/unclear`. Use `default_model`. Unit test with 5 sample headlines (mix of ICP / not ICP / ambiguous).

**Step 3 — Touch recorder**
Build `processor/touch_recorder.py`. Parse delayed scrape output, detect operator handle, classify and record all touch types. Update `warming_score` on profile. Unit test with sample scrape fixture.

**Step 4 — Delayed scrape orchestrator**
Build `processor/delayed_scrape.py`. Select top N posts by expected ICP yield formula. Call Apify `harvestapi~linkedin-profile-posts` with comments+reactions ON. Feed output to touch_recorder. Dry-run test first (no real Apify call), then live test with 1 post.

**Step 5 — Profile scrape batcher**
Build `processor/profile_scraper.py`. Rank `icp_candidates`, scrape top N, run full ICP check, update state. Dry-run first, then live test with 2 profiles.

**Step 6 — Influencer ranker**
Build `processor/influencer_ranker.py`. Score influencers, update `icp_pct`, check watchlist auto-add threshold. Unit test with fixture data.

**Step 7 — Wire into main pipeline**
Add people pipeline call to main orchestrator. Order: collect posts → delayed scrape (for posts 3 days old) → headline check new profiles → profile scrape batch → influencer rank update.

**Step 8 — Integration test**
Full dry run of complete pipeline. Verify all tables populated correctly. Check `progress.md` is up to date.
