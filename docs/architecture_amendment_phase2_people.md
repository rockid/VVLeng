# Architecture Amendment — People Pipeline & Relationship Engine
Date: 2026-06-14
Status: APPROVED — implement in Phase 2

This document extends the original architecture with the people pipeline, relationship state machine, influencer ranking system, and delayed scrape logic. Hand to Cline alongside CLINE.md when starting Phase 2.

---

## Overview

The system has two parallel pipelines:
1. **Post pipeline** (original) — collect posts, score, generate comment/repost actions
2. **People pipeline** (this amendment) — discover people, qualify as ICP, warm up, feed outreach

The people pipeline is the bridge between content intelligence and LinkedIn outreach. Its output is a daily ranked shortlist of ICP candidates ready for connection requests.

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

## 13. Cline Build Order

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
