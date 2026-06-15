# LinkedIn Engagement System — Amendment & Implementation Guide

**Replaces:** All previous amendment documents (treat as if they never existed)  
**Amends:** `linkedin_engagement_system_architecture.md` (v1.0)  
**Date:** 2026-06-13  
**Status:** v1.0 backbone built, not yet test-run. Start at Phase 0.

Hand this document to Cline alongside the base architecture (v1.0). This document takes precedence wherever it conflicts with v1.0.

---

## Table of Contents

1. [Config Architecture (replaces .env-only approach)](#1-config-architecture)
2. [Client Folder Structure](#2-client-folder-structure)
3. [Three-Route Post Discovery](#3-three-route-post-discovery)
4. [Keyword Architecture — Three Tiers](#4-keyword-architecture--three-tiers)
5. [Niche & TA Definition — Structured Config](#5-niche--ta-definition--structured-config)
6. [Semantic Pre-Filter](#6-semantic-pre-filter)
7. [Post Scoring](#7-post-scoring)
8. [Relationship State Tracking](#8-relationship-state-tracking)
9. [Topic Signal Extraction](#9-topic-signal-extraction)
10. [Repost Action Type](#10-repost-action-type)
11. [Route 3 — Follow Graph Traversal](#11-route-3--follow-graph-traversal)
12. [Schema Changes](#12-schema-changes)
13. [Project Structure Changes](#13-project-structure-changes)
14. [Implementation Sequence for Cline](#14-implementation-sequence-for-cline)

---

## 1. Config Architecture

### Problem with the current approach

The v1.0 spec uses a flat `.env` file for everything — secrets, operational settings, and client-specific values mixed together. This breaks multi-client support and makes client onboarding fragile.

### New three-layer config

```
.env                          ← secrets only (never commit)
config.yaml                   ← shared operational defaults + active client ID
clients/{client_id}.yaml      ← all client-specific settings
```

**`.env` — secrets only:**

```bash
# ── Apify ─────────────────────────────────────────────────────────────
APIFY_API_TOKEN=apify_api_xxxxx

# ── LLM ───────────────────────────────────────────────────────────────
LLM_API_KEY=sk-xxxxx
LLM_BASE_URL=https://api.laozhang.ai/v1

# ── Database ──────────────────────────────────────────────────────────
# Phase 1: SQLite (default, zero setup)
DATABASE_URL=sqlite:///./data/engagement.db
# Phase 2+: switch to Postgres (no code change needed)
# DATABASE_URL=postgresql://app:password@localhost:5432

# ── Redis (Phase 2+) ──────────────────────────────────────────────────
# REDIS_URL=redis://localhost:6379/0
```

**`config.yaml` — shared operational defaults:**

```yaml
# ── Active client ─────────────────────────────────────────────────────
# Override with --client CLI flag or select from dashboard (future)
active_client: "alumni_saas"

# ── Apify actor IDs ───────────────────────────────────────────────────
actors:
  post_search: "harvestapi/linkedin-post-search"
  # fallback: "apimaestro/linkedin-posts-search-scraper-no-cookies"
  post_scraper: "apify/linkedin-post-scraper"
  profile_scraper: "apify/linkedin-profile-scraper"
  follower_scraper: "apify/linkedin-followers-scraper"

# ── LLM models ────────────────────────────────────────────────────────
llm:
  comment_model: "gpt-4o-mini"
  hook_model: "gpt-4o-mini"
  signal_model: "gpt-4o-mini"
  scoring_model: "gpt-4o-mini"

# ── Global pipeline defaults (overridable per client) ─────────────────
defaults:
  max_posts_per_keyword: 50
  min_post_length_chars: 100
  max_post_age_days: 7
  dedup_window_days: 14
  apify_max_runs_per_hour: 10
  fetch_usage_after_run: true   # set false during dev to skip cost tracking

# ── Paths ─────────────────────────────────────────────────────────────
paths:
  clients_dir: "./clients"
  data_dir: "./data"
  logs_dir: "./logs"
```

### Config loading in code

```python
# config_loader.py

def load_config(client_id_override: str = None) -> AppConfig:
    """
    1. Load .env (secrets)
    2. Load config.yaml (shared config)
    3. Determine active client: CLI override → config.yaml active_client
    4. Load clients/{client_id}.yaml
    5. Merge: client YAML values override config.yaml defaults
    6. Return single AppConfig object used everywhere
    """
```

`AppConfig` is a dataclass (or Pydantic model) — all downstream modules import `AppConfig`, never read files directly. No module should open `.env` or any YAML file itself.

### CLI override

```bash
python run_pipeline.py                        # uses active_client from config.yaml
python run_pipeline.py --client alumni_saas   # overrides active_client
```

---

## 2. Client Folder Structure

### Principle

All client assets — data, outputs, exports, logs — live under `data/{client_id}/`. This folder is created automatically on first run if it does not exist.

```
data/
  alumni_saas/             ← created on first run, name = client_id
    raw/                   ← Stage 1: raw Apify output JSON by date
    filtered/              ← Stage 2: post-filter JSON (debug use)
    plans/                 ← daily plan JSON files
    output/                ← scored posts, signal CSVs, weekly briefs
    exports/               ← periodic client export packages
    errors/                ← failed actor run logs

clients/
  _template.yaml           ← copy this to create a new client
  alumni_saas.yaml         ← active client config
```

### First-run folder creation

```python
# in config_loader.py, after loading client config

def ensure_client_dirs(client_id: str, data_dir: str):
    """Create data/{client_id}/ subdirectories if they don't exist. Silent if already exist."""
    subdirs = ["raw", "filtered", "plans", "output", "exports", "errors"]
    for subdir in subdirs:
        Path(data_dir) / client_id / subdir).mkdir(parents=True, exist_ok=True)
```

Call this at startup before any pipeline step runs.

### Client config template

**`clients/_template.yaml`** — copy and rename to `clients/{client_id}.yaml`:

```yaml
# ── Identity ──────────────────────────────────────────────────────────
client_id: "alumni_saas"          # must match filename stem and data folder name
display_name: "Alumni Network SaaS Client"

# ── Niche definition (see §5 for usage) ───────────────────────────────
niche:
  product_description: |
    B2B SaaS platform for building and managing structured online communities.
    Core features: member engagement tools, event management, member directory,
    community monetisation, analytics, and onboarding flows.

  primary_use_case: "Alumni networks for universities and business schools"

  expanding_use_cases:
    - "Cohort-based online course communities"
    - "Startup accelerator and incubator communities"
    - "Entrepreneurial and professional communities"
    - "Professional associations and membership organisations"

  target_audience:
    - "Alumni relations managers and directors at universities"
    - "Online course creators and cohort-based learning operators"
    - "Startup accelerator program managers"
    - "Community managers at professional associations"
    - "Founders building community-led products"
    - "SaaS operators measuring community ROI"

  pain_vocabulary:
    # Known pain terms. Grows over time from signal extraction output (§9).
    - "ghost members"
    - "dead community"
    - "member churn"
    - "low engagement"
    - "nobody posts"
    - "community ROI"
    - "member retention"

# ── Keywords — three tiers (see §4) ───────────────────────────────────
keywords:
  tier1_direct:
    - "alumni network"
    - "alumni engagement"
    - "alumni community"
    - "community management platform"
    - "member engagement"
    - "ghost members"
    - "community ROI"
    - "community onboarding"

  tier2_lateral:
    - "cohort-based learning"
    - "online course community"
    - "startup accelerator community"
    - "professional association management"
    - "membership organisation"
    - "community-led growth"
    - "customer community"
    - "member retention"
    - "audience engagement"

  tier3_platforms:
    - "Circle.so"
    - "Mighty Networks"
    - "Hivebrite"
    - "Bettermode"
    - "Higher Logic"
    - "Graduway"
    - "Almabase"
    - "Skool"

# ── Collection settings ────────────────────────────────────────────────
collection:
  posts_per_keyword: 30             # start conservative, increase after validation
  min_engagement_tier1: 10
  min_engagement_tier2: 50
  min_engagement_tier3: 5
  graph_traversal_enabled: false    # do not enable until Routes 1+2 are stable

# ── Semantic filter (see §6) ──────────────────────────────────────────
filter:
  min_semantic_similarity: 0.35     # tune after first run
  blocked_substrings:
    - "hiring"
    - "job opening"
    - "we are recruiting"
    - "happy to share that I have joined"
    - "congratulations on your new role"
    - "open to work"

# ── Scoring (see §7) ──────────────────────────────────────────────────
scoring:
  tier_a_threshold: 0.65
  tier_b_threshold: 0.40
  influencer_follower_threshold: 5000
  min_score_for_signal: 6           # posts at/above this get signal extraction (§9)

# ── Action limits ─────────────────────────────────────────────────────
action_limits:
  connections_per_day: 15
  comments_per_day: 8
  visits_per_day: 25
  reposts_per_week: 3

# ── Influencer watchlist (Route 1) ────────────────────────────────────
# Seed manually with 15-20 known relevant accounts before first run
influencer_watchlist:
  - "https://www.linkedin.com/in/example1"
  - "https://www.linkedin.com/in/example2"

# ── Cost limits ───────────────────────────────────────────────────────
cost_limits:
  daily_apify_budget_usd: 3.00
  monthly_apify_budget_usd: 60.00
```

---

## 3. Three-Route Post Discovery

Replace the single keyword collection loop from v1.0 with three distinct discovery routes.

```
Route 1: Influencer Watchlist    Route 2: Keyword Search
(2×/day, bounded, reliable)      (2×/day, wider surface)
         │                                │
         └──────────────┬─────────────────┘
                        ▼
              POST POOL (deduplicated)
              → semantic filter
              → post scorer
              → action planner
                        │
         Route 3: Follow Graph (separate job, not daily)
         → expands influencer watchlist over time
         → disabled until Routes 1+2 are stable (≥2 weeks)
```

### Route 1 — Influencer Watchlist (`collector/route_watchlist.py`)

Checks every profile in `influencer_watchlist` for posts in the last 24 hours.

```python
def collect_watchlist_posts(config: AppConfig) -> list[Post]:
    """
    For each URL in config.client.influencer_watchlist:
      - fetch posts from last 24h via Apify profile posts actor
      - return posts above min_engagement_tier1
    Route 1 posts skip the semantic filter — pre-validated by watchlist membership.
    """
```

**Schedule:** 2×/day at 07:00 and 13:00.  
**Seed the watchlist manually** with 15–20 accounts before first run.

### Route 2 — Keyword Search (`collector/route_keywords.py`)

```python
def collect_keyword_posts(config: AppConfig) -> list[Post]:
    """
    For each keyword across all three tiers:
      - search LinkedIn posts from last 7 days
      - apply per-tier engagement threshold
      - tag each post with keyword_matched and keyword_tier
      - deduplicate against posts already seen in DB
    """
```

**Schedule:** 2×/day, same as Route 1.  
Per-tier engagement thresholds from client config (§2).

### Route 3 — Follow Graph

Documented separately in §11. Not part of daily run. Disabled by default.

### Post pool deduplication

All routes feed a shared pool. Before any post enters the pipeline:

```python
def is_already_seen(post_url: str, client_id: str) -> bool:
    """True if post_url exists in posts table for this client within dedup_window_days."""
```

Posts already commented on, or older than `max_post_age_days`, are excluded from the action plan regardless of score.

---

## 4. Keyword Architecture — Three Tiers

Three tiers with different noise profiles, engagement thresholds, and semantic filter multipliers.

| Tier | Type | Volume | Noise | Engagement threshold | Semantic multiplier |
|---|---|---|---|---|---|
| tier1_direct | Practitioner vocabulary | Low | Low | 10 | 1.0× (base) |
| tier2_lateral | Adjacent TA pain | High | High | 50 | 1.2× (stricter) |
| tier3_platforms | Competitor/platform names | Medium | Low | 5 | 0.85× (looser) |

**Tier rationale:**
- Tier 1: Even quiet posts on direct terms are on-topic — low engagement bar
- Tier 2: Broad terms attract noise — higher engagement bar and stricter semantic gate
- Tier 3: Platform mentions signal product-aware practitioners — always worth seeing regardless of engagement count or semantic distance from niche description

**Vocabulary expansion:** `topic_tags` and `pain_points` from signal extraction (§9) accumulate new vocabulary over time. Review `signal_{date}.csv` weekly for new terms to promote into tier1 or tier2. This is the primary mechanism for growing the keyword list.

---

## 5. Niche & TA Definition — Structured Config

The client YAML `niche:` block (shown in §2) replaces the single `niche_description` string from v1.0.

### Usage in code

```python
# config_loader.py

def build_niche_embedding_text(niche: dict) -> str:
    """
    Dense concatenated text for semantic embedding.
    Combines all niche fields into one string.
    """
    return " ".join([
        niche["product_description"],
        niche["primary_use_case"],
        " ".join(niche["expanding_use_cases"]),
        " ".join(niche["target_audience"]),
        " ".join(niche["pain_vocabulary"]),
    ])

def build_niche_prompt_context(niche: dict) -> str:
    """
    Structured multi-line string for injection into LLM system prompts.
    Used by comment_gen.py, signal_extractor.py, hook_gen.py.
    """
    # Returns formatted string with labelled sections
    ...
```

All prompt templates that previously injected `{niche_description}` must be updated to inject `{niche_prompt_context}` from `build_niche_prompt_context()`.

---

## 6. Semantic Pre-Filter

**New file:** `processor/semantic_filter.py`

Reduces post volume before LLM calls by ~70–80%. Zero API cost. Runs on CPU — works on Windows laptop.

```python
from sentence_transformers import SentenceTransformer, util
from functools import lru_cache

MODEL_NAME = "all-MiniLM-L6-v2"   # 80MB download on first use, cached after

@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)

def build_niche_embedding(niche_text: str):
    """Call once at pipeline startup. Cache the result in AppConfig."""
    return get_model().encode(niche_text, convert_to_tensor=True)

def passes_filter(
    post: Post,
    niche_embedding,
    config: AppConfig
) -> tuple[bool, float]:
    """
    Returns (passed: bool, score: float).
    Applies blocked_substrings check first (cheap), then semantic scoring.
    Tier multiplier applied to base threshold from client config.
    """
    # 1. Blocked substring check
    text_lower = post.text.lower()
    for blocked in config.client.filter.blocked_substrings:
        if blocked.lower() in text_lower:
            return False, 0.0

    # 2. Length check
    if len(post.text) < config.client.defaults.min_post_length_chars:
        return False, 0.0

    # 3. Semantic score
    post_embedding = get_model().encode(post.text, convert_to_tensor=True)
    score = float(util.cos_sim(niche_embedding, post_embedding))

    multiplier = {
        "tier1": 1.0,
        "tier2": 1.2,
        "tier3": 0.85,
    }.get(post.keyword_tier, 1.0)

    threshold = config.client.filter.min_semantic_similarity * multiplier
    return score >= threshold, score
```

### Integration point in pipeline

```
Route 2 collect → semantic_filter → post_scorer → planner
Route 1 collect → (skip filter)  → post_scorer → planner
```

### Threshold calibration

Start at `min_semantic_similarity: 0.35`. After first real run, check the filter log:
- Drop rate >90% → lower threshold to 0.25
- LLM receiving clearly irrelevant posts → raise to 0.40–0.45
- Target operating range: 0.30–0.45

**Dependencies to add to `requirements.txt`:**
```
sentence-transformers>=2.7.0
# CPU-only torch — add this index URL comment for Cline to handle:
# pip install torch --index-url https://download.pytorch.org/whl/cpu
```

---

## 7. Post Scoring

**New file:** `processor/post_scorer.py`

Scores posts for commenting and repost value. Separate from profile (lead) scoring.

```python
@dataclass
class PostScore:
    score: float           # 0.0–1.0 composite
    freshness: float
    velocity: float
    relevance: float
    opportunity: float
    post_type: str         # "comment_target" | "repost_candidate" | "avoid"
    avoid_reason: str      # populated if post_type == "avoid"

def score_post(post: Post, config: AppConfig) -> PostScore:
    ...
```

### Scoring dimensions

| Dimension | Weight | Logic |
|---|---|---|
| Freshness | 0.35 | < 6h = 1.0 · < 12h = 0.8 · < 24h = 0.5 · older = 0 |
| Engagement velocity | 0.25 | (likes + comments) / hours since posted |
| Topic relevance | 0.25 | Keyword tier weight: tier1 = 1.0 · tier2 = 0.7 · tier3 = 0.85 |
| Comment opportunity | 0.15 | 5–30 comments = 1.0 (visible but not buried) · 0 comments = 0.5 · >100 = 0 |

### Post type flags

**`avoid` — tag post, exclude from plan:**
- Post already has >100 comments
- Author is a direct competitor (keyword match against a `competitor_domains` list in client YAML — add when needed)
- Post is purely celebratory — detected by heuristic keyword list (hiring, new role, work anniversary, congratulations)
- Client has already commented on this post

**`repost_candidate`:**
- Author is in influencer_watchlist (high authority)
- Topic tier1 or tier3 relevance
- Published >12h ago (past best commenting window)
- Client has not reposted this author in last 14 days

Repost candidates surface in the dashboard as a separate action type with a weekly cap (`reposts_per_week` from client config).

---

## 8. Relationship State Tracking

Prevents re-targeting the same people indefinitely.

### State machine

```
new → contacted → warm → converted
           ↓
         cold    (30 days no response)
```

**Transitions:**
- `new → contacted`: connection request sent OR comment made on their post
- `contacted → warm`: connection accepted OR they replied to a comment OR engaged with client post
- `warm → converted`: became a qualified lead (booked call, clicked link, DMed)
- `contacted → cold`: 30 days since last action, no response

### Schema addition to `profiles` table

```python
relationship_status  = Column(String(20), default="new")
    # new | contacted | warm | converted | cold
first_contacted_at   = Column(DateTime, nullable=True)
last_interaction_at  = Column(DateTime, nullable=True)
interaction_count    = Column(Integer, default=0)
```

### Planner filter rules

| Status | Eligible for |
|---|---|
| `new` | Any action |
| `contacted` | Follow-up only (reply to their comment, engage with their post) — no new connection request |
| `warm` | Any action |
| `cold` | Excluded unless manually re-activated |
| `converted` | Excluded entirely |

---

## 9. Topic Signal Extraction

**New file:** `content/signal_extractor.py`

Extracts market intelligence from high-scoring posts as a byproduct of the engagement pipeline. Solves the "5 post topics per week" need without any external signal source.

### What it extracts (per post)

- `topic_tags` — 1–4 short topic labels
- `pain_points` — specific frustrations mentioned (empty list if none)
- `content_angle` — one sentence: what is this post actually about?
- `vocabulary_hooks` — memorable phrases worth reusing in client content
- `signal_score` — 1–10: how useful as content intelligence?

### LLM prompt

```python
SIGNAL_SYSTEM_PROMPT = """
You are a market intelligence analyst for a B2B SaaS company.

{niche_prompt_context}

Extract structured signal from LinkedIn posts. Return ONLY a JSON array,
one object per post, same order as input. No preamble, no markdown, no backticks.

Each object:
- post_index: int
- topic_tags: list[str]  (1-4 short labels)
- pain_points: list[str]  (specific problems mentioned; [] if none)
- content_angle: str  (one sentence)
- vocabulary_hooks: list[str]  (memorable phrases from the post worth reusing)
- signal_score: int  (1-10)
"""
```

### Integration point

Only runs on posts where `post_score.score >= config.client.scoring.min_score_for_signal`. Not every post — only engagement-worthy ones.

```
semantic_filter → post_scorer → [score >= threshold] signal_extractor → planner
```

### Weekly topic brief

**New file:** `planner/weekly_brief.py`

Runs Sunday aggregation over the past 7 days of signal data:

```python
def generate_weekly_brief(config: AppConfig) -> WeeklyBrief:
    """
    Aggregates topic_tags and pain_points from the week's signal posts.
    Returns top 10 topics by frequency, top 5 pains, and 5 suggested post angles.
    Writes to data/{client_id}/output/weekly_brief_{YYYY-WNN}.csv
    """
```

This weekly brief is the content planning output — operator reads it on Monday morning to plan the week's posts.

---

## 10. Repost Action Type

Add `repost` to the `action_type` enum in the `actions` table.

### Repost action fields

```python
# Additional fields on the actions table for repost type
repost_angle         = Column(String(30), nullable=True)
    # "data_point" | "contrarian" | "niche_application"
original_author_name = Column(String(200), nullable=True)
```

### Repost commentary prompt rules

Add `content/prompts/repost_commentary_system.txt`:

```
Generate LinkedIn repost commentary. Rules:
- Opening: one sentence naming the specific idea (not generic praise — never "great post")
- Body: 2–4 sentences — a data point, contrarian take, or niche application
- Close: one question that invites the audience in
- Hard limit: 300 characters total
- No emoji unless the original post uses them
- Generate 2 variants with different angles
```

### Weekly cap enforcement

`reposts_per_week` from client config. Enforced by the planner — not additive to the posting schedule. A repost replaces one original post slot.

---

## 11. Route 3 — Follow Graph Traversal

**New file:** `collector/route_graph.py`

**This is a Phase 3 feature. Do not implement until Routes 1+2 have run stably for ≥2 weeks and there are ≥50 confirmed tier-A profiles in the DB.**

The flag `graph_traversal_enabled: false` in client config must be explicitly set to `true` by the operator. The pipeline must check this flag and skip Route 3 entirely if false — no prompts, no warnings.

### Conceptual model

Breadth-first search on the LinkedIn follow graph, seeded from confirmed TA profiles.

```
Confirmed TA profile (depth 0)
  → fetch their follow list
  → score each followed profile (cheap: headline only)
  → tier A/B → add to traverse_queue at depth 1
  → high follower count → add to influencer_candidates table
       ↓
Depth-1 profile
  → fetch their follow list (if budget allows)
  → score → add to traverse_queue at depth 2
  → STOP at max_depth (default: 2)
```

### Two-stage enrichment (cost control)

- **Stage 1 (cheap):** fetch headline + follower_count only. Run relevance scorer. Cost: ~$0.004/profile.
- **Stage 2 (expensive, selective):** full enrichment only for profiles passing Stage 1 relevance threshold. Cost: ~$4–10/1,000 profiles.

### Termination conditions

Stop when any of these is true:
- `depth >= max_depth`
- Credits consumed >= `daily_credit_budget`
- `traverse_queue` has no untraversed entries at current depth
- <5% of profiles at current depth passing Stage 1 (quality degrading — log and stop)

### New tables

**`traverse_queue`:**

```python
class TraverseQueue(Base):
    __tablename__ = "traverse_queue"
    id                = Column(UUID, primary_key=True, default=uuid4)
    profile_id        = Column(UUID, ForeignKey("profiles.id"))
    depth             = Column(Integer, default=0)
    source_profile_id = Column(UUID, ForeignKey("profiles.id"), nullable=True)
    queued_at         = Column(DateTime, default=datetime.utcnow)
    traversed_at      = Column(DateTime, nullable=True)
    result            = Column(String(20), nullable=True)
        # "expanded" | "skipped" | "budget_exceeded"
```

**`influencer_candidates`:**

```python
class InfluencerCandidate(Base):
    __tablename__ = "influencer_candidates"
    id           = Column(UUID, primary_key=True, default=uuid4)
    profile_id   = Column(UUID, ForeignKey("profiles.id"))
    in_degree    = Column(Integer)      # how many TA profiles follow this person
    first_seen_at = Column(DateTime)
    promoted_at  = Column(DateTime, nullable=True)
    status       = Column(String(20), default="candidate")
        # "candidate" | "promoted" | "dismissed"
```

Graph traversal surfaces influencer candidates for operator review — it does not auto-populate the watchlist. Operator promotes manually from dashboard.

---

## 12. Schema Changes

All additions to existing tables. No tables removed.

### `posts` table — add fields

```python
# From semantic filter
semantic_score       = Column(Float, nullable=True)
passed_semantic      = Column(Boolean, default=True)
keyword_tier         = Column(String(10), nullable=True)    # tier1 | tier2 | tier3
keyword_matched      = Column(String(200), nullable=True)

# From post scorer
post_score           = Column(Float, nullable=True)
post_type            = Column(String(30), nullable=True)    # comment_target | repost_candidate | avoid
avoid_reason         = Column(Text, nullable=True)
route_source         = Column(String(20), nullable=True)    # route1 | route2 | route3

# From signal extractor
topic_tags           = Column(Text, nullable=True)          # JSON-serialized list
pain_points          = Column(Text, nullable=True)          # JSON-serialized list
content_angle        = Column(Text, nullable=True)
vocabulary_hooks     = Column(Text, nullable=True)          # JSON-serialized list
signal_score         = Column(Integer, nullable=True)
```

Note: `ARRAY` and `JSONB` are Phase 2+ (PostgreSQL). In Phase 1 SQLite, store lists as JSON-serialized `Text`. Use `json.dumps()` / `json.loads()` helpers in the model. No code change needed when switching to Postgres — just change the column type and add a migration.

### `profiles` table — add fields

```python
relationship_status  = Column(String(20), default="new")
first_contacted_at   = Column(DateTime, nullable=True)
last_interaction_at  = Column(DateTime, nullable=True)
interaction_count    = Column(Integer, default=0)
traverse_queued_at   = Column(DateTime, nullable=True)
traversed_at         = Column(DateTime, nullable=True)
traverse_depth       = Column(Integer, nullable=True)
```

### `actions` table — extend

```python
action_type          = Column(String(20))
    # existing: comment | connection | visit | post
    # add:      repost
repost_angle         = Column(String(30), nullable=True)
original_author_name = Column(String(200), nullable=True)
```

### New tables

- `traverse_queue` — see §11
- `influencer_candidates` — see §11
- `apify_usage` — cost tracking:

```python
class ApifyUsage(Base):
    __tablename__ = "apify_usage"
    id             = Column(UUID, primary_key=True, default=uuid4)
    client_id      = Column(String(50))
    actor_id       = Column(String(100))
    run_id         = Column(String(100))
    route          = Column(String(20))         # route1 | route2 | route3
    items_returned = Column(Integer)
    compute_units  = Column(Float)
    estimated_cost = Column(Float)
    run_at         = Column(DateTime)
```

### `weekly_signal_briefs` table

```python
class WeeklySignalBrief(Base):
    __tablename__ = "weekly_signal_briefs"
    id          = Column(UUID, primary_key=True, default=uuid4)
    client_id   = Column(String(50))
    week_number = Column(Integer)
    year        = Column(Integer)
    top_topics  = Column(Text)    # JSON-serialized [{tag, count}]
    top_pains   = Column(Text)    # JSON-serialized [{pain, count}]
    post_angles = Column(Text)    # JSON-serialized [{angle, source_post_ids}]
    created_at  = Column(DateTime, default=datetime.utcnow)
```

---

## 13. Project Structure Changes

Full target structure — new files marked `# NEW`:

```
linkedin-engagement/
│
├── run_pipeline.py              # updated: --client flag, loads AppConfig
├── config.yaml                  # NEW: shared operational config
├── config_loader.py             # NEW: loads all config layers into AppConfig
├── .env                         # secrets only (new template, see §1)
├── .env.example                 # updated template
├── docker-compose.yml           # unchanged (Phase 2+)
├── requirements.txt             # updated: add sentence-transformers
│
├── clients/                     # NEW
│   ├── _template.yaml           # NEW
│   └── alumni_saas.yaml         # NEW: first client config
│
├── collector/
│   ├── apify_client.py          # unchanged
│   ├── normaliser.py            # updated: keyword_tier + route_source fields
│   ├── incremental.py           # unchanged
│   ├── route_watchlist.py       # NEW: Route 1
│   └── route_keywords.py        # NEW: Route 2 (refactored from existing collector)
│   └── route_graph.py           # NEW: Route 3 (Phase 3, stub only for now)
│
├── processor/
│   ├── scorer.py                # unchanged: profile/lead scoring
│   ├── dedup.py                 # unchanged
│   ├── semantic_filter.py       # NEW: §6
│   ├── post_scorer.py           # NEW: §7
│   ├── topic_graph.py           # unchanged (Phase 2)
│   └── influencer_map.py        # unchanged (Phase 2)
│
├── content/
│   ├── llm_client.py            # unchanged
│   ├── comment_gen.py           # updated: inject niche_prompt_context
│   ├── signal_extractor.py      # NEW: §9
│   ├── gap_analysis.py          # unchanged (Phase 2)
│   ├── hook_gen.py              # updated: inject niche_prompt_context
│   └── prompts/
│       ├── comment_system.txt   # updated: niche_prompt_context injection
│       ├── comment_user.txt     # unchanged
│       ├── hook_system.txt      # updated: niche_prompt_context injection
│       ├── repost_commentary_system.txt  # NEW: §10
│       └── repost_commentary_user.txt    # NEW: §10
│
├── planner/
│   ├── daily_plan.py            # updated: relationship status filter, repost type
│   ├── output.py                # unchanged
│   └── weekly_brief.py          # NEW: §9 weekly aggregation
│
├── db/
│   ├── models.py                # updated: all schema changes from §12
│   ├── session.py               # updated: derive DB name from client_id
│   └── migrations/              # Alembic (Phase 2+)
│
├── dashboard/
│   ├── app.py                   # updated: signal tab
│   └── views/
│       ├── daily_plan.py        # updated: repost action type display
│       ├── analytics.py         # unchanged
│       ├── leads.py             # updated: relationship status display
│       └── signal.py            # NEW: weekly brief view
│
└── data/
    └── {client_id}/             # created on first run
        ├── raw/
        ├── filtered/
        ├── plans/
        ├── output/
        ├── exports/
        └── errors/
```

---

## 14. Implementation Sequence for Cline

Work through these phases in order. **Do not start the next phase until all done conditions for the current phase are met.** Each phase builds on a stable foundation.

---

### Phase 0 — Stabilize the existing v1.0 build

**Goal:** Get the existing codebase running end-to-end before adding anything new.

| Step | Task | Done when |
|---|---|---|
| 0.1 | Read the existing codebase. Identify any import errors, missing files, or broken references left from the initial build. Fix them. Do not add features. | `python run_pipeline.py --dry-run` runs without errors |
| 0.2 | Create a new `.env` from the template in §1. Fill in placeholder values only (no real keys yet). | `.env` exists, no missing key errors on startup |
| 0.3 | Run `python run_pipeline.py --dry-run`. Fix any runtime errors. | Dry run prints all pipeline steps and exits cleanly |
| 0.4 | Run Phase 1 pipeline with real Apify credentials and 3 seed keywords, `MAX_POSTS_PER_KEYWORD=5`. | Raw JSON written to `data/raw/`. At least 1 post collected. |
| 0.5 | Verify normaliser output: check that collected posts have all expected fields. Log any missing fields. | `Post` objects have non-null `post_id`, `text`, `url`, `author_name` |
| 0.6 | Run full pipeline end-to-end: collect → score → plan → dashboard. | Daily plan JSON generated. Dashboard loads and displays at least 1 action. |

**Do not proceed to Phase 1 until Phase 0 is complete.**

---

### Phase 1 — Config architecture + client structure

**Goal:** Implement the new three-layer config system and client folder structure. No new pipeline features yet.

| Step | Task | Done when |
|---|---|---|
| 1.1 | Create `config.yaml` with content from §1. | File exists and is valid YAML |
| 1.2 | Create `clients/` directory. Create `clients/_template.yaml` from §2. Create `clients/alumni_saas.yaml` with the alumni SaaS niche content from §2. | Both files exist |
| 1.3 | Write `config_loader.py`. Implement `load_config()` — loads `.env`, loads `config.yaml`, determines active client, loads client YAML, merges into `AppConfig` dataclass. Implement `ensure_client_dirs()`. | `from config_loader import load_config` works. `load_config()` returns populated `AppConfig`. |
| 1.4 | Update `run_pipeline.py`: add `--client` CLI flag. Call `load_config(client_id_override)` at startup. Call `ensure_client_dirs()`. | `python run_pipeline.py --client alumni_saas` starts without error and creates `data/alumni_saas/` subdirectories |
| 1.5 | Update all modules that currently read from `.env` directly to receive `AppConfig` instead. No module should open `.env` or any YAML file itself. | No `os.environ` calls outside `config_loader.py` |
| 1.6 | Update all file output paths to write under `data/{client_id}/` instead of flat `data/`. | Raw output goes to `data/alumni_saas/raw/`, plans to `data/alumni_saas/plans/` |
| 1.7 | Implement `build_niche_embedding_text()` and `build_niche_prompt_context()` in `config_loader.py` (§5). Update all prompt templates to inject `{niche_prompt_context}`. | Comment generation prompt contains client niche context |
| 1.8 | Run full pipeline end-to-end with new config. | Same output as Phase 0 step 0.6, now reading from `config.yaml` + `clients/alumni_saas.yaml` |

---

### Phase 2 — Route split + keyword tiers + schema updates

**Goal:** Split collection into Route 1 and Route 2. Add tiered keywords. Update DB schema.

| Step | Task | Done when |
|---|---|---|
| 2.1 | Update `db/models.py` with all schema changes from §12 (new fields on `posts`, `profiles`, `actions`; new tables `apify_usage`, `weekly_signal_briefs`). Use JSON-serialized `Text` for list fields (SQLite phase). | Alembic migration runs (or DB recreated) without errors |
| 2.2 | Create `collector/route_watchlist.py` — Route 1 (§3). Fetch posts from `influencer_watchlist` profiles. Tag posts with `route_source = "route1"`. Route 1 posts are flagged to skip semantic filter. | Collect with empty watchlist returns 0 posts without error. Add 1 test profile, rerun — post collected. |
| 2.3 | Create `collector/route_keywords.py` — Route 2 (§3). Refactor existing keyword collection into this module. Read three-tier keyword structure from client config. Tag each post with `keyword_matched` and `keyword_tier`. Apply per-tier engagement thresholds. | Posts collected with correct `keyword_tier` values in output |
| 2.4 | Update `run_pipeline.py` to call both routes, merge results, and deduplicate before passing to processor. | Combined post pool contains posts from both routes, no duplicates |
| 2.5 | Create stub `collector/route_graph.py` — Route 3. Reads `graph_traversal_enabled` flag. If false (default), logs "Route 3 disabled" and returns empty list. No further implementation. | Pipeline runs with Route 3 stub, no errors |
| 2.6 | Add `apify_usage` tracking: after each actor run, fetch usage stats from Apify API and write a record to `apify_usage` table. Check daily budget before triggering each actor. | After one run, `apify_usage` table has records. Run halts if budget exceeded. |
| 2.7 | Run full pipeline with new route structure. | Posts collected from both routes, correctly tagged, written to DB |

---

### Phase 3 — Semantic filter + post scorer + relationship tracking

**Goal:** Add the three new processing modules between collection and planning.

| Step | Task | Done when |
|---|---|---|
| 3.1 | Add `sentence-transformers` to `requirements.txt`. Install (CPU-only torch). Verify import works on Windows. | `from sentence_transformers import SentenceTransformer` imports without error |
| 3.2 | Create `processor/semantic_filter.py` (§6). Build niche embedding at startup from `build_niche_embedding_text()`. | Module imports. `passes_filter()` returns `(bool, float)` for a test post string. |
| 3.3 | Integrate semantic filter into pipeline: Route 2 posts pass through filter before scoring. Route 1 posts skip it. Log per-keyword pass/fail counts and drop reasons. | After one run: filter log shows per-keyword drop rates. Check that drop rate is reasonable (target 50–80%, not 95%+). Tune threshold if needed. |
| 3.4 | Create `processor/post_scorer.py` (§7). Implement all four scoring dimensions and post type classification. | `score_post()` returns `PostScore` with all fields populated. |
| 3.5 | Integrate post scorer into pipeline after semantic filter. | Posts in DB have `post_score` and `post_type` fields populated after run. |
| 3.6 | Add relationship status fields to `profiles` table (§8). Update planner to filter by relationship status: `cold` and `converted` excluded; `contacted` eligible for follow-up only. | Daily plan respects relationship status filters. |
| 3.7 | Run full pipeline. Review `data/alumni_saas/output/` for any output files. Manually inspect 5–10 scored posts. | Scored posts look reasonable. High-scoring posts are genuinely engagement-worthy. Adjust scoring weights if needed. |

---

### Phase 4 — Signal extraction + repost type + weekly brief

**Goal:** Add market intelligence extraction and repost action type.

| Step | Task | Done when |
|---|---|---|
| 4.1 | Create `content/signal_extractor.py` (§9). Implement batched LLM extraction for posts with `post_score >= min_score_for_signal`. | `signal_extractor.py` runs on a batch of 5 test posts and returns JSON with all required fields. |
| 4.2 | Integrate signal extractor into pipeline after post scorer. Write output to `data/{client_id}/output/signal_{date}.csv`. | After one run: `signal_{date}.csv` exists with topic_tags, pain_points, content_angle columns populated. |
| 4.3 | Add `repost` action type to `actions` table (§10). Add `repost_angle` and `original_author_name` fields. Create `content/prompts/repost_commentary_system.txt` with rules from §10. | DB accepts repost action records. |
| 4.4 | Update `processor/post_scorer.py` to route `repost_candidate` posts to repost queue. Update planner to enforce `reposts_per_week` cap and include repost actions in daily plan. | Repost candidates appear in daily plan JSON with generated commentary. Weekly cap enforced. |
| 4.5 | Create `planner/weekly_brief.py` (§9). Implement Sunday aggregation job. | `generate_weekly_brief()` runs without error. `weekly_brief_{YYYY-WNN}.csv` written to output folder. |
| 4.6 | Add Signal tab to Streamlit dashboard showing this week's brief: top topics, top pain points, 5 suggested post angles. | Dashboard shows Signal tab. Data loads from latest weekly brief file. |
| 4.7 | Full end-to-end run. Review weekly brief manually. | Weekly brief contains recognizable topics from the niche. Suggested post angles are usable. |

---

### Phase 5 — Route 3 follow graph (defer until Phase 4 is stable)

**Prerequisite:** Routes 1+2 have run stably for ≥2 weeks. ≥50 confirmed tier-A profiles in DB. Operator has manually set `graph_traversal_enabled: true` in client YAML.

Only implement when the above prerequisites are met. Full spec in §11.

---

*End of Amendment & Implementation Guide.*
